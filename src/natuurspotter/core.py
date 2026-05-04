import calendar
import html
import math
import os
import re
import tempfile
import time
import webbrowser
from datetime import date
from io import BytesIO
from urllib.parse import quote_plus, urlparse

import folium
import matplotlib.pyplot as plt
import pandas as pd
import requests
import wikipedia
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fpdf import FPDF


REQUEST_TIMEOUT = 20
USER_AGENT = "NatuurSpotter/1.0.1"
DEFAULT_HEADERS = {"User-Agent": USER_AGENT}

load_dotenv()


def _required_env_var(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _http_get(url, **kwargs):
    headers = DEFAULT_HEADERS.copy()
    headers.update(kwargs.pop("headers", {}) or {})
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    response = requests.get(url, headers=headers, **kwargs)
    response.raise_for_status()
    return response


def _translate_text(text, src, dest):
    try:
        from googletrans import Translator
    except Exception:
        return text

    try:
        return Translator().translate(text, src=src, dest=dest).text
    except Exception:
        return text


def _pdf_image_bytes(image_url, image_bytes):
    if not image_bytes:
        return None, None

    try:
        from PIL import Image, UnidentifiedImageError
    except Exception:
        return None, None

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image_format = (image.format or "").upper()

            if image_format in {"JPEG", "PNG"}:
                suffix = ".jpg" if image_format == "JPEG" else f".{image_format.lower()}"
                return suffix, image_bytes

            converted = BytesIO()
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGB")
            image.save(converted, format="PNG")
            return ".png", converted.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        print(f"Skipping unsupported image format: {image_url}")
        return None, None


def _looks_like_scientific_name(name):
    return bool(re.match(r"^[A-Z][a-z]+(?:\s+[a-z][a-z-]+){1,2}$", name.strip()))


def _species_search_query(name):
    return quote_plus(name.strip().replace("-", " "))


def _species_link_from_href(href):
    if href is None or not href.startswith("/species/"):
        return ""

    if not href.endswith("/"):
        href += "/"

    return f"https://waarnemingen.be{href}"


def _species_href_from_search_query(query):
    search_url = f"https://waarnemingen.be/search/?q={_species_search_query(query)}"
    r = _http_get(search_url)
    soup = BeautifulSoup(r.text, "html.parser")

    a = soup.select_one("li.lead a[href^='/species/']")
    if a is None:
        return ""

    return a.get("href", "")




def getinfo(latinName):
    """
    Fetches the first paragraph of the Wikipedia page for the given Latin name.
    input: 
        - latinName (str) - The Latin name of the species.
    output: 
        - The first paragraph of the Wikipedia page.
    """
    
    wikipedia.set_lang("nl")
    try:
        page = wikipedia.page(latinName)
    except wikipedia.exceptions.WikipediaException:
        return ""
    except Exception:
        return ""
    
    
    #text = page.content.lower() chechk this ltr

    paragraphs = page.content.split("\n") 

    cparagraphs = []
    for p in paragraphs:
        if p.strip():
            cparagraphs.append(p)

    if not cparagraphs:
        return ""
    
    output = cparagraphs[0] + "\n\n"
    
    output = _translate_text(output, src="nl", dest="en")

    return output  # return first two paragraphs as a string






def getRarity(latinName, limit=10):
    """
    Fetches rarity status and recent observations of a species from waarnemingen.be.
    input: 
        - latinName (str) - The Latin name of the species.
        - limit (int) - The maximum number of observations to return.
    output: 
        - (commonName (str), scientificName (str), rarityStatus (str), data (DataFrame)) - The common name, scientific name, rarity status, and recent observations as a DataFrame.
        - None if the species or rarity page cannot be found.
    """
    rarityUrl = getspecies_name(latinName)
    if not rarityUrl:
        return None

    href = urlparse(rarityUrl).path
    if not href.endswith("/"):
        href += "/"

    r = _http_get(rarityUrl)
    
    soup = BeautifulSoup(r.text, "html.parser")

    rarityStatus = soup.select_one("div > span.hidden-sm") #finding the rarity status
    if rarityStatus is None:
        return None
    else:
       rarityStatus = rarityStatus.text.strip()
       
    tag = soup.select_one("i.species-scientific-name") #scientific name
    if tag is None:
        scientific = ""
    else:
        scientific = tag.get_text(strip=True)
        
    ctag = soup.select_one("span.species-common-name") #this will le me the common name
    if ctag is None:
        cname = ""
    else:
        cname = ctag.get_text(strip=True)


    date_after = "2010-12-28"
    date_before = date.today().strftime("%Y-%m-%d")

    obvsUrl = (
        f"https://waarnemingen.be{href}observations/"
        f"?date_after={date_after}"
        f"&date_before={date_before}"
        f"&country_division=15"
        f"&search=&user=&location=&sex=&month=&life_stage=&activity=&method="
    )
    r = _http_get(obvsUrl)
    
    soup = BeautifulSoup(r.text, "html.parser")

    table = soup.find("table", class_="table") # scrapping wannrmingen
    if table is None:
        empty = pd.DataFrame(columns=["date", "number", "location"])
        return cname, scientific, rarityStatus, empty

    tbody = table.find("tbody")
    if tbody is None:
        empty = pd.DataFrame(columns=["date", "number", "location"])
        return cname, scientific, rarityStatus, empty

    results = []
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        
        number = tds[1].get_text(strip=True)
        match = re.search(r"\d+", number)

        if match is not None:
            number = match.group()
        else:
            number = ""

        results.append({
            "date": tds[0].get_text(strip=True),
            "number": number,
            "location": tds[2].get_text(strip=True)
        })

        if len(results) == limit:
            break
    
    data = pd.DataFrame(results, columns=["date", "number", "location"])
    

    return cname, scientific, rarityStatus, data




def get_image(species_name):
    
    """
    Fetches the first image from Wikimedia Commons related to the species name.
    input: 
        - species_name - The name of the species.
    output: 
        -(imageUrl, imageBytes) - The URL of the image and the image bytes.
    """
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": species_name,
        "gsrlimit": 1, # limiting the search to one 
        "gsrnamespace": 6, #images
        "prop": "imageinfo",
        "iiprop": "url" # returns url
    }

    r = _http_get(
        "https://commons.wikimedia.org/w/api.php",
        params=params,
    )

    data = r.json()

    query = {} #avoids error
    if "query" in data:
        query = data["query"]

    pages = {} # avoids error
    if "pages" in query:
        pages = query["pages"] # this will get me the pages from the json response
    

    if not pages:
        return None, None

    page = None
    for p in pages.values():
        page = p
        break # the first page 
    
    imageinfo = page.get("imageinfo")

    if not imageinfo:
        return None, None

    info = imageinfo[0]

    imageUrl = info.get("url") 
    if imageUrl is None:
        return None, None

    img_response = _http_get(imageUrl)
    
    
    imageBytes = img_response.content # imgae bytes i will convert it on the pdf

    return imageUrl, imageBytes



def species_info(latinName):
    """
    Fetches species information and writes a PDF report.
    
    input: 
        -latinName (str) - The Latin name of the species.
    output: 
        -Generates a PDF file with species information.
    
    """

    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_dir = os.path.join(base_dir, "fonts")
    font_regular = os.path.join(font_dir, "DejaVuSans.ttf")
    font_bold = os.path.join(font_dir, "DejaVuSans-Bold.ttf") # this willl get the cwd and the fonts

    description = getinfo(latinName)

    image_url, image_bytes = get_image(latinName)

    
    result = getRarity(latinName) 
    if not result:
        print("No rarity/observation data found.")
        return

    common_name, scientific_name, rarity_status, observations = result # getting rarity, common name and obs data 

    
    pdf = FPDF() # initiating the pdf
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    
    pdf.add_font("DejaVu", "", font_regular)
    pdf.add_font("DejaVu", "B", font_bold)

   
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 10, common_name or latinName, new_x="LMARGIN", new_y="NEXT") # title
    pdf.ln(2)

    image_suffix, pdf_image_bytes = _pdf_image_bytes(image_url, image_bytes)
    if pdf_image_bytes: # transforming my image byttess through temp file to pdf image
        temp_image_path = None
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=image_suffix)
            temp_image_path = tmp.name
            try:
                tmp.write(pdf_image_bytes)
            finally:
                tmp.close()

            pdf.image(temp_image_path, w=60)
            pdf.ln(5)
        finally:
            if temp_image_path and os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    
    pdf.set_font("DejaVu", "B", size=12) 
    pdf.cell(0, 8, f"Latin name: {scientific_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Rarity status: {rarity_status}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    
    pdf.set_font("DejaVu", size=11)
    pdf.multi_cell(0, 7, str(description))
    pdf.ln(4)

    pdf.set_font("DejaVu", "B", 12) # obs title
    pdf.cell(0, 8, "Recent observations (West Flanders)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    
    col_date = 35 # size of my table columns
    col_number = 18
    col_location = pdf.w - pdf.l_margin - pdf.r_margin - col_date - col_number # so my table doesnt over step the page width


    pdf.set_font("DejaVu", "B", 10) #header for the table
    pdf.cell(col_date, 7, "Date", border=1, align="L")
    pdf.cell(col_number, 7, "Number", border=1, align="C")
    pdf.cell(col_location, 7, "Location", border=1, align="L", new_x="LMARGIN", new_y="NEXT")

    
    pdf.set_font("DejaVu", size=10) #ROWS fro the table
    if observations.empty: # if there is no obeservation
        pdf.cell(col_date + col_number + col_location, 7, "No recent observations found.",
                 border=1, align="L", new_x="LMARGIN", new_y="NEXT")
    else:
        for _, row in observations.iterrows():
            date_text = str(row.get("date", ""))
            number_text = str(row.get("number", ""))
            location_text = str(row.get("location", ""))

            pdf.cell(col_date, 7, date_text, border=1, align="L")
            pdf.cell(col_number, 7, number_text, border=1, align="C")
            pdf.cell(col_location, 7, location_text, border=1, align="L",
                     new_x="LMARGIN", new_y="NEXT")

    
    base_dir = os.getcwd() # this allowws me to get the current working directory, and create an output folder if not exists
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True) 

    filename = f"{latinName.replace(' ', '_')}.pdf"
    filepath = os.path.join(output_dir, filename)

    pdf.output(filepath)

def Sdata(day=None):
    """
    Scrapes one page of the daylist table.
    input:
        day= None 
    output:
        rows with sum// or w/o sum
    """
    if day is None:
        day = date.today().strftime("%Y-%m-%d")

    # DD-MM-YYYY, convert to YYYY-MM-DD
    if isinstance(day, str) and re.match(r"^\d{2}-\d{2}-\d{4}$", day):
        parts = day.split("-")
        day = parts[2] + "-" + parts[1] + "-" + parts[0]
        
    #reject other weird formats
    if not isinstance(day, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        return []
    
    species_group = 8  # group 8 us moths
    country_division = 15  # West flaanders is division 15
    #rarity=""
    #search=""
    pagenum = 1
    
    url = "https://waarnemingen.be/fieldwork/observations/daylist/"

    rows = []
    lastp = None  # remembers the previous page content

    while True:
        params = {
            "date": day,
            "species_group": species_group,
            "country_division": country_division,
            #"rarity": rarity,
            #"search": search,
            "page": pagenum
        }

        r = _http_get(url, params=params)
        
        

        soup = BeautifulSoup(r.text, "html.parser")

        table = soup.find("table")
        if table is None:
            break

        tbody = table.find("tbody")
        if tbody is None:
            break

        page_rows = 0  # track if this page has data
        page = []  # store the rows of THIS page to see if the data is the same

        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 5:
                continue
            
            sumtext = tds[2].get_text(strip=True)
            try:
                sumvalue = int(sumtext)
            except ValueError:
                sumvalue = 0 # if the number is not found then it just adds zero

            sorrt = tds[3].get_text(" ", strip=True)
            location = tds[4].get_text(" ", strip=True)
            
            #location = location.replace("(WV)", "West-Flanders, Belgium")

            rows.append({
                "date": day,
                "species": sorrt,
                "location": location,
                "sum": sumvalue
            })

            page.append((sorrt, location, sumvalue))
            page_rows += 1

        if page_rows == 0:
            break   #  has no valid rows it ends 

        # if dta the same end 
        if lastp is not None:
            if page == lastp:
                break

        lastp = page
        pagenum += 1  #next
        
    
    if rows: # removing duplicates
        df = pd.DataFrame(rows)
        df = df.drop_duplicates(subset=["date", "species", "location", "sum"]) # removing duplicates
        rows = df.to_dict(orient="records")
        
    
        

    return rows



def geopoints(location):
    url = "https://api.geoapify.com/v1/geocode/search"
    api_key = _required_env_var("GEOAPIFY_API_KEY")
    params = {
        "text": f"{location}, West-Vlaanderen, Belgium",
        "lang": "nl",
        "limit": 1,
        "type": "city",
        "format": "json",
        "filter": "countrycode:be",
        "apiKey": api_key
    }

    r = _http_get(url, params=params)

    data = r.json()
    results = data.get("results", [])

    if len(results) == 0:
        return None, None

    first = results[0]
    lat = first.get("lat")
    lng = first.get("lon")
    return lat, lng

def wV(lat, lng):
    
    """
    Checks whether a geographic point is located inside West Flanders
    This helps filter bad location addresses 
    input:
        - lat: latitude of the point
        - lng: longitude of the point
    output : 
        - True if the point lies within west flanders, False otherwise
    """
    return (50.7 <= lat <= 51.4) and (2.5 <= lng <= 3.5)

def rowstopoints(rows, geocode_delay=0.1):
    """
    Converts locations to points.
    Input: 
        - rows = list of dicts from Sdata()
           each row has: {"date": "...", "species": "...", "location": "..."}
        - geocode_delay = pause in seconds after each geocoding request.
    Output: 
        - points: list of dicts, ONE dict per location point:
           {"date": "...", "species": "...", "location": "...", "lat": ..., "lng": ...}
    """
    points = []

    for row in rows:
        day = row.get("date", "")
        species = row.get("species", "")
        location = row.get("location", "")
        
        if re.search(r"\d+\s+locaties", location.lower()): # ignores if location is not there 
            continue


        
        parts = location.split(",") #

        for part in parts:
            
            loc = part.strip()
            loc = re.sub(
                r"\s*\((?:WV|OV|AN|VB|LB|WB|HT|LG|LX|NA|BR)\)\s*$",
                "",
                loc,
            ).strip("() ")
        
            if loc == "":
                continue

            lat, lng = geopoints(loc)#  logitude and latitude
            if geocode_delay:
                time.sleep(geocode_delay)
            
            if lat is None or lng is None: 
                continue
            
            if not wV(lat, lng):
                continue

            #restoringg
            points.append({
                "date": day,
                "species": species,
                "location": loc,
                "lat": lat,
                "lng": lng})

    return points


def speciescolor(species, species_colors):
    """
    Assigns and remembers one color per species for the observation map
    input:
        species:The species name for the observation
        species_colors: A dictionary that stores already assigned colors in the form: {species_name: color}
    output:
        color : A color string that is always the same for the same species.
    """

    palette = ["#e41a1c", "#b2182b", "#cb181d", "#fb6a4a", "#fcae91", "#377eb8", "#08519c", "#2171b5", "#4292c6", "#6baed6", "#9ecae1",
    "#4daf4a", "#006d2c", "#238b45", "#41ab5d", "#74c476", "#a1d99b", "#984ea3", "#6a3d9a", "#807dba", "#9e9ac8", "#bcbddc", "#dadaeb",
    "#ff7f00", "#fdae61", "#fdd49e", "#ffd92f", "#fee391", "#8c510a", "#a6611a", "#bf812d", "#dfc27d", "#f6e8c3", "#41b6c4","#1f9ac9", 
    "#3690c0", "#67a9cf", "#7fcdbb", "#c7e9b4", "#f781bf", "#fa9fb5", "#fcbba1", "#fde0dd", "#000000", "#252525",
    "#525252", "#737373", "#969696", "#bdbdbd", "#d9d9d9", "#1b9e77", "#66c2a5", "#99d8c9", "#d95f02", "#fc8d62",
    "#7570b3", "#8da0cb", "#e7298a", "#f768a1", "#66a61e", "#a6d854", "#e6ab02", "#ffd92f", "#a6761d", "#d8b365",
    "#666666", "#999999", "#4c4cfb", "#00cc99", "#ff6699", "#9933ff", "#00b3b3", "#ff9933", "#66ff33", "#cc0066",
    "#3399ff", "#996633", "#893339", "#384c40"]

    if species in species_colors:
        return species_colors[species] # if the species is already used, this will directly assigne the same colour

    # assign next color
    color = palette[len(species_colors) % len(palette)]
    species_colors[species] = color

    return color

def observations_map(day=None, open_browser=False, geocode_delay=0.1):
    """
    Generates an interactive observation map for moth observations in West Flanders
    input:
        day (str or None)
            Date in format YYYY-MM-DD.
            If None, the current date is used.
        open_browser (bool)
            Open the generated map in the default browser when True.
        geocode_delay (float)
            Pause in seconds after each geocoding request.

    output:
        str or None
            Saves an HTML map file to the output directory and returns its path.
            Returns None when no data is available.
    """
    if day is None:
        day = date.today().strftime("%Y-%m-%d")

    rows = Sdata(day)
    if not rows:
        return None
    points = rowstopoints(rows, geocode_delay=geocode_delay)

    m = folium.Map(location=[51.05, 3.0], zoom_start=9)

    species_colors = {} # sttoring the species and its assigned colours

    for p in points:
        
        if p["lat"] is None or p["lng"] is None: # removig bad points 
            continue

        color = speciescolor(p["species"], species_colors)
        popup_species = html.escape(str(p["species"]))
        popup_location = html.escape(str(p["location"]))
        popup_date = html.escape(str(p["date"]))

        folium.CircleMarker(
            location=[p["lat"], p["lng"]],
            radius=5,
            popup=f"""
            <b>{popup_species}</b><br>
            {popup_location}<br>
            {popup_date}
            """,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8
        ).add_to(m)
        
    boxhtml = """
    <div style="
        position: fixed;
        bottom: 40px;
        left: 40px;
        z-index: 9999;
        background-color: white;
        padding: 10px;
        border: 2px solid black;
        border-radius: 5px;
        font-size: 12px;
    ">
    <b>Species legend</b><br>
    """

    for species, color in species_colors.items(): 
        escaped_species = html.escape(str(species))
        boxhtml += f"""
        <div>
            <span style="
                display:inline-block;
                width:12px;
                height:12px;
                background:{color};
                margin-right:5px;
            "></span>
            {escaped_species}
        </div>
        """

    boxhtml += "</div>" # to clos the sec

    m.get_root().html.add_child(folium.Element(boxhtml))
        

    base_dir = os.getcwd() # now i'm getting the current working directory 
    output_dir = os.path.join(base_dir, "output") # saving the path
    os.makedirs(output_dir, exist_ok=True) 

    filename = f"observations_map_{day}.html"
    filepath = os.path.join(output_dir, filename)

    m.save(filepath) # saves the file to the. output- folder

    if open_browser:
        webbrowser.open(f"file://{os.path.abspath(filepath)}") # opens the webpage 

    return filepath

def getspecies_name(latinName):  # reused code piiece from getRarity
    """
    Searches waarnemingen.be for a species and returns the species page link

    input:
        latinName --> scientific or common name of the species.

    output:
        speciesNameLink --> full URL to the species page on waarnemingen.be.
    Returns an empty string if the species is not found.
    """

    href = _species_href_from_search_query(latinName)
    if href:
        return _species_link_from_href(href)

    if _looks_like_scientific_name(latinName):
        return ""

    translated_name = _translate_text(latinName, src="en", dest="nl")
    if translated_name == latinName:
        return ""

    href = _species_href_from_search_query(translated_name)
    return _species_link_from_href(href)
    



def getmonthtoseasonn(month): #classifyingg 
    """
    Converts a numeric month to a meteorological season.

    input: 
        month --> Month number (1-12)

    output:
        season --> "Winter", "Spring", "Summer", "Autumn"
    """
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5):
        return "Spring"
    if month in (6, 7, 8):
        return "Summer"
    return "Autumn"




def observationtble(table):
    """
    Extracts observation data from the observations HTML table

    input:
        table--> observation rows.

    output:
        rows --> A list of dictionaries where each dictionary represents one day:
                - "date"  : observation date (YYYY-MM-DD)
                - "count": number of observations on that date
                - "season" : season derived from the month (Winter, Spring, Summer, Autumn)
    """
    rows = []

    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue


        datetext = tds[0].get_text(" ",   strip=True)
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b",datetext) # getting date format with regex
        if date_match is None:
            continue
        observation_date = date_match.group(1)

        numbertext = tds[1].get_text(" ", strip=True  ) # addding space 
        nspecies = re.search(r"\b(\d+)\b",numbertext)
        if nspecies is None:
            continue
        count = int(nspecies.group(1)) #num of species convert to int

        month = int(observation_date[5:7])
        season = getmonthtoseasonn(month) # converting month to seansons

        rows.append({
            "date": observation_date,
            "count": count,
            "season": season
        })
        
        

    return rows



def season(year, species_id, request_delay=0.2):
    """
    Scrapes and processes observation data for a specific species
    in West Flanders for a given year

    input:
        year --> Year for which observations are collected.
        species_id ---> Species ID extracted from the waarnemingen.be species page.
        request_delay --> pause in seconds between paginated requests.
    output: data -->  dataframe containing:
            - date (datetime)
            - count (number of observations)
            - season (Winter, Spring, Summer, Autumn)
    if empty:
            Returns an empty DataFrame with the expected columns.
    """

    allrows = []
    page = 1
    last_page = None

    while True:
        url = (
            f"https://waarnemingen.be/species/{species_id}/observations/"
            f"?date_after={year}-01-01"
            f"&date_before={year}-12-31"
            f"&country_division=15"
            f"&page={page}"
        )

        r = _http_get(url)

        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.select_one("div.table-container table")

        if table is None:
            break

        rows = observationtble(table)
        if not rows:
            break

        page_signature = [(row["date"], row["count"], row["season"]) for row in rows]
        if last_page is not None and page_signature == last_page:
            break

        last_page = page_signature

        allrows.extend(rows)
        page += 1
        if request_delay:
            time.sleep(request_delay)
        

    data = pd.DataFrame(allrows)

    if data.empty:
        return pd.DataFrame(columns=["date", "count", "season"])

    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").reset_index(drop=True)

    return data

def seasonal_analysis(species, year):
    """
    Analyzes seasonal observation patterns for a given moth species
    in West Flanders for a specific year

    input:
        species --> Name of the moth species 
        year --> year for which the observations are analyzed

    output:
            - seasonal bar chart and prints
            - a short ecological explanation in the console
    """
    
    species_url = getspecies_name(species)
    if species_url == "":
        print("species not found")
        return

    m = re.search(r"/species/(\d+)/", species_url)
    if m is None:
        print("could not extract species id")
        return
    species_id = m.group(1)

    data = season(year, species_id)
    if data.empty:
        print("no observation data found")
        return

    season_summary = data.groupby("season")["count"].sum()


    plt.figure(figsize=(8, 5))
    season_summary.plot(kind="bar")
    plt.title(f"Seasonal observations of {species} ({year})")
    plt.xlabel("Season")
    plt.ylabel("Number of observations")
    plt.tight_layout(pad= 0)
    plt.show()

    lowest_season = season_summary.idxmin()
    highest_season = season_summary.idxmax()

    together_api_key = os.getenv("TOGETHER_API_KEY")
    if not together_api_key:
        print("TOGETHER_API_KEY not set, skipping LLM explanation.")
        return

    os.environ.setdefault("TOGETHER_NO_BANNER", "1")
    try:
        from together import Together
    except ImportError:
        print("together package not installed, skipping LLM explanation.")
        return

    client = Together(api_key=together_api_key)
    
    season_summary_text = season_summary.rename("observations").to_frame().to_string()
    prompt = (
        f"Seasonal observation counts for moth species '{species}' in West Flanders during {year}:\n"
        f"{season_summary_text}\n\n"
        f"Lowest season: {lowest_season}. Highest season: {highest_season}.\n"
        "Explain briefly why this species may be less or more observed during these seasons. "
        "Use ecological and biological reasoning. No section headings or emoji; write one 6-7 sentence statement."
    )

    response = client.chat.completions.create(
        model="google/gemma-3n-E4B-it",
        messages=[{"role": "user", "content": prompt}]
    )

    explanation = response.choices[0].message.content
    
    print("\n")
    print(explanation)

def biodiversity_analysis(month=None, year=None, request_delay=0.2):
    """
    Analyzes biodiversity data for a given month in a given year (West Flanders)
    input:
        - month --> integer 
        - year --> integer
        - request_delay --> pause in seconds between daily requests
    output:
        - return CSV summary_df
        - return CSV raw_df 
    """

    today = date.today()

    if month is None:
        month = today.month

    if year is None:
        year = today.year

    month = int(month)
    year = int(year)

    days_in_month = calendar.monthrange(year, month)[1] # grab num of days 

    all_rows = []

    for day_num in range(1, days_in_month + 1):

        day_str = f"{year:04d}-{month:02d}-{day_num:02d}"

        daily_rows = Sdata(day_str)
        all_rows.extend(daily_rows)

        if request_delay and day_num < days_in_month:
            time.sleep(request_delay)

    fulldatadf = pd.DataFrame(all_rows)

  
    if fulldatadf.empty: 

        summary_df = pd.DataFrame([{
            "year": year,
            "month": month,
            "totalObservations": 0,
            "species_richness": 0,
            "observation_frequency": 0,
            "unique_locations": 0,
            "most_observed_species": "",
            "most_observed_count": 0,
            "top_species_share": 0,
            "shannon_diversity": 0,
            "simpson_diversity": 0
        }]) # so the node red 

        base_dir = os.getcwd()
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        summary_path = os.path.join(
            output_dir,
            f"biodiversity_summary_{year}-{month:02d}.csv"
        )

        raw_path = os.path.join(
            output_dir,
            f"biodiversity_raw_{year}-{month:02d}.csv"
        )

        summary_df.to_csv(summary_path, index=False)
        fulldatadf.to_csv(raw_path, index=False)

        print("Saved summary CSV:", summary_path)
        print("Saved raw CSV:", raw_path)

        return summary_df, fulldatadf

    
    fulldatadf["species"] = fulldatadf["species"].astype(str).str.strip() # converting to strings 
    fulldatadf["location"] = fulldatadf["location"].astype(str).str.strip()#coverting to string
    
    fulldatadf["sum"] = fulldatadf["sum"].astype(int) #to int for csalculations
    
    fulldatadf = fulldatadf.drop_duplicates(subset=["date", "species", "location", "sum"])


    total_observations = int(fulldatadf["sum"].sum())

    species_richness = int(fulldatadf["species"].nunique())

    unique_locations = int(fulldatadf["location"].nunique())

    observation_frequency = total_observations / days_in_month


    species_counts = fulldatadf.groupby("species")["sum"].sum()
    species_counts = species_counts.sort_values(ascending=False)

    most_observed_species = species_counts.index[0]
    most_observed_count = int(species_counts.iloc[0])

    top_species_share = most_observed_count / total_observations

    
    shannon = 0.0
    simpson_sum = 0.0
    
    #Shannon div = - sum of(p * log(p)) 
    # simpsom diversoty = 1 - sum of (p_i²)
    for count in species_counts.values:
        proportion = count / total_observations

        if proportion > 0:
            shannon += -proportion * math.log(proportion)
            simpson_sum += proportion * proportion

    simpson = 1.0 - simpson_sum


    summary_df = pd.DataFrame([{ # add calclations and add csvfile
        "year": year,
        "month": month,
        "totalObservations": total_observations,
        "species_richness": species_richness,
        "observation_frequency": observation_frequency,
        "unique_locations": unique_locations,
        "most_observed_species": most_observed_species,
        "most_observed_count": most_observed_count,
        "top_species_share": top_species_share,
        "shannon_diversity": shannon,
        "simpson_diversity": simpson
    }])
    
    

    base_dir = os.getcwd()
    output_dir =   os.path.join(base_dir, "output") # saves to the same oupt file in the current working directory
    os.makedirs (output_dir, exist_ok=True) 

    summarycsvpath = os.path.join(
        output_dir,
        f"biodiversity_summary_{year}-{month:02d}.csv"
    )
    rawcsvpath = os.path.join(
        output_dir,
        f"biodiversity_raw_{year}-{month:02d}.csv"
    )

    summary_df.to_csv(summarycsvpath, index=False) # to csv
    fulldatadf.to_csv(rawcsvpath, index=False) 

    print("Saved summary CSV:", summarycsvpath)
    print("Saved raw CSV:", rawcsvpath)

    return summary_df, fulldatadf
