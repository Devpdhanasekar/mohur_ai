from flask import Flask, jsonify, request
# from scrap_openai import main
import requests
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests
import openai
import json
# from helper import dbCommunication
from tavily import TavilyClient
from pymongo import MongoClient
from bson.json_util import dumps
from dotenv import load_dotenv
import os
load_dotenv()
# Create Flask application
app = Flask(__name__)
CORS(app)
openai.api_key = os.getenv("OPEN_AI_APIKEY")



from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError




def getFounderLinkedIn(query, location="United States"):
    url = "https://serpapi.com/search"
    
    # Define the parameters for the API request
    params = {
        "engine": "google",
        "q": query,
        "location": location,
        "num": 1,  # Request only the top result
        "api_key": "0d8dffb04c8e2f446e228f2f76df8724ba82972abe5fe8d11e4cc855624b0f50"
    }
    
    # Make the request to the SERP API
    response = requests.get(url, params=params)
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()  # Parse the JSON response
        if 'organic_results' in data and len(data['organic_results']) > 0:
            print(data['organic_results'][0])
            return data['organic_results'][0]["link"]  # Return the top result
        else:
            return None  # No organic results found
    else:
        return None 

tavily = TavilyClient(api_key="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")
    
# @app.route('/fundSize',methods=["POST"])
def tavily_search(query):
    url = "https://api.tavily.com/search"
    # url = request.get_json()
    print(url)
    qna_response = tavily.qna_search(query=query)
    return{"response":qna_response}



def get_lat_long(location):
    geolocator = Nominatim(user_agent="my_app")
    
    try:
        # Attempt to geocode the location
        location_info = geolocator.geocode(location)
        
        if location_info:
            latitude = location_info.latitude
            longitude = location_info.longitude
            return {latitude, longitude}
        else:
            return "Location not found"
    
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        return f"Error: {str(e)}"



def parse_results(data):
    if not data:
        return []

    # results = data.get('local_results', [])
    parsed_results = []

    for place in data:
        parsed_results.append({
            'name': place.get('title'),
            'address': place.get('address'),
            'phone': place.get('phone'),
            'rating': place.get('rating'),
            'reviews': place.get('reviews'),
            'price': place.get('price'),
            'type': place.get('type'),
            'website': place.get('website'),
            'open_state': place.get('open_state'),
            'hours': place.get('hours'),
            'gps_coordinates': place.get('gps_coordinates'),
            'thumbnail': place.get('thumbnail')
        })

    return parsed_results




def scrape_google_maps(api_key, query, count, lattitude, longitude):
    location = f"@{lattitude},{longitude},{15.1}z"
    all_results = []
    
    for page in range(count):  # Scrape 3 pages
        params = {
            "api_key": api_key,
            "engine": "google_maps",
            "q": query,
            "ll": location,
            "type": "search",
            "start": page * 20  # Each page typically has 20 results
        }
        
        response = requests.get('https://serpapi.com/search', params=params)
        data = response.json()
        
        if 'local_results' in data:
            results = data['local_results']
            all_results.extend(results)
        
        if 'serpapi_pagination' not in data or not data['serpapi_pagination'].get('next'):
            break  # No more pages to scrape
    
    return all_results




@app.route('/googlemap', methods=["POST"])
def getGoogleMapData():
    print("dfghjkafghjkadfghjkafghjkadfghjkadfghjkdfghjaaaaaaaaaaaaaaafghjk")
    url = request.get_json()
    print(url)
    api_key = "0d8dffb04c8e2f446e228f2f76df8724ba82972abe5fe8d11e4cc855624b0f50"  # Replace with your actual SerpApi key
    location = url["location"]
    query = url["query"]
    pagination_count = url["pageCount"] * 20
    print(pagination_count)
    
    lat, long = get_lat_long(location)
    print(lat, long)

    results = scrape_google_maps(api_key, query, pagination_count, lat, long)
    data = parse_results(results)
    
    
    return {"result":results}

@app.route('/investment', methods=["GET"])
def getInvestmentData():
    try:
        client = MongoClient('mongodb+srv://devpdhanasekar:VRBpMHku36ashoCe@cluster0.upee9tc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
        db = client['crafy_db']
        collection = db['investment_funds']
        data = collection.find()
        # Convert the cursor to a list of documents
        data_list = list(data)
        # Convert the list to JSON
        response = dumps(data_list)
        return response, 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return f"Error: {str(e)}"



def scrape_fund_data(url):
    # Send a GET request to the URL
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to retrieve the web page. Status code: {response.status_code}")
        return None

    # Parse the HTML content of the page
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract the text content of the page
    text_data = soup.get_text(separator='\n', strip=True)
    
    return text_data




def process_with_openai(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use the new model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        print(response.choices[0].message['content'].strip())
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/webscrap', methods=["POST"])
def scrapDataFromWeb():
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb+srv://devpdhanasekar:VRBpMHku36ashoCe@cluster0.upee9tc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
        db = client['crafy_db']
        collection = db['investment_funds']

        # Check if the data already exists
        url_data = request.get_json()
        website_url = url_data["url"]["website"]
        isAvailable = collection.find_one({"website": website_url})
        
        if isAvailable:
            return {"message": "Data already exists"}

        # Proceed with scraping if data does not exist
        raw_data = scrape_fund_data(website_url)
        prompt = f"""
            {raw_data}
            The objective of you is to create a complete and accurate JSON output based on the web-scraped details stored in the variable webScarp. The JSON output should fill all the keys provided in the template with relevant information extracted from webScarp. The goal is to generate a comprehensive and informative JSON representation of the company's details.
            Step 1: Analyze the Web-Scraped Details
            Analyze the web-scraped details stored in the variable webScarp. This string contains information about a company.
            Step 2: Identify Relevant Information
            Identify the relevant information within webScarp that corresponds to the keys in the given JSON content.
            Step 3: Fill JSON Keys
            Fill the JSON keys with non-empty values extracted from webScarp. Ensure that all keys are filled with accurate and relevant information.
            Step 4: Create Complete JSON Output
            Create a complete and accurate JSON output by filling all the keys with non-empty values.
            Do Not Leave Any Values Empty
            Do not leave any values empty. Fill all the keys with relevant information from webScarp.
            Follow These Steps Exactly
            Follow these steps exactly to generate the JSON output. Do not deviate from the instructions or make any assumptions.
            JSON Template
            The JSON template is as follows:
            json
            "Fund Name": "",
            "Brief Description": "",
            "HQ Location": "",
            "Investor Type": "",
            "Equity / Debt (Fund Category)":"",
            "Stages of Entry/ Investment": "",
            "Sectors of Investment": "",
            "Geographies Invested In": "",
            "Portfolio Companies": "",
            "No.of Portfoilo Companies Invested in" : "",
            "No.of Exits": "",
            "Portfolio Acquisitions": "",
            "Website": "",
            "Portfolio Unicorns / Soonicorns": "",
            "Portfolio Exits": "",
            "Operating Status (Active/ Deadpooled/ etc)" : "",
            "Deals in last 12 months": "",
            "AUM (Dollar)": "",
            "Size of the Fund": "",
            "Founded Year": "",
            "Team size": "",
            "Group Email ID/ Email ID" : "",
            "Contact Number": "",
            "LinkedIn": "",
            "Twitter": "",
            "Youtube" : "",
            "Co-Investors": "",
            "Founders": "",
            "Tags/ Keywords": ""
        """

        print("Prompt for OpenAI:", prompt)

        # Step 3: Use OpenAI model to process the data
        processed_data = process_with_openai(prompt)
        start = processed_data.find("{")
        end = processed_data.find("}")
        processed_data = processed_data[start:end+1]
        finalResult = json.loads(processed_data)

        # Construct the data for MongoDB
        data = {
            'fund_name': url_data["url"]["title"],
            'brief_description': finalResult.get("Brief Description", ""),
            'hq_location': finalResult.get("HQ Location", ""),
            'investor_type': url_data["url"]["type"],
            'equity_debt_fund_category': finalResult.get("Equity / Debt (Fund Category)", ""),
            'stages_of_entry_investment': finalResult.get("Stages of Entry/ Investment", ""),
            'sectors_of_investment': finalResult.get("Sectors of Investment", ""),
            'geographies_invested_in': finalResult.get("Geographies Invested In", ""),
            'portfolio_companies': finalResult.get("Portfolio Companies", ""),
            'no_of_portfolio_companies_invested_in': finalResult.get("No.of Portfoilo Companies Invested in", ""),
            'no_of_exits': finalResult.get("No.of Exits", ""),
            'portfolio_acquisitions': finalResult.get("Portfolio Acquisitions", ""),
            'website': website_url,
            'portfolio_unicorns_soonicorns': finalResult.get("Portfolio Unicorns / Soonicorns", ""),
            'portfolio_exits': finalResult.get("Portfolio Exits", ""),
            'operating_status_active_deadpooled_etc': finalResult.get("Operating Status (Active/ Deadpooled/ etc)", ""),
            'deals_in_last_12_months': finalResult.get("Deals in last 12 months", ""),
            'size_of_the_fund': finalResult.get("Size of the Fund", ""),
            'aum_dollar': finalResult.get("AUM (Dollar)", ""),
            'founded_year': finalResult.get("Founded Year", ""),
            'team_size': finalResult.get("Team Size", ""),
            'group_email_id_email_id': finalResult.get("Group Email ID/ Email ID", ""),
            'contact_number': finalResult.get("Contact Number", ""),
            'linkedin': finalResult.get("LinkedIn", ""),
            'twitter': finalResult.get("Twitter", ""),
            'youtube': finalResult.get("Youtube", ""),
            'co_investors': finalResult.get("Co-Investors", ""),
            'founders': finalResult.get("Founders", ""),
            'tags_keywords': finalResult.get("Tags/ Keywords", "")
        }

        inserted_id = collection.insert_one(data).inserted_id

        # Additional data fetching and updating if necessary
        if not data['size_of_the_fund']:
            fundSize = tavily_search(url_data["url"]["title"] + " company overall fund size")
            collection.update_one({'_id': inserted_id}, {'$set': {'size_of_the_fund': fundSize["response"]}})

        if not data['linkedin']:
            founderLinkedIn = getFounderLinkedIn(url_data["url"]["title"] + " company founder linkedin profile")
            collection.update_one({'_id': inserted_id}, {'$set': {'linkedin': founderLinkedIn}})

        if not data['deals_in_last_12_months']:
            lastDeals = tavily_search(url_data["url"]["title"] + " last 12 months funding deals")
            collection.update_one({'_id': inserted_id}, {'$set': {'deals_in_last_12_months': lastDeals["response"]}})

        if not data['founders'] or not data['co_investors'] or not data['team_size'] or not data['portfolio_acquisitions'] or not data['portfolio_unicorns']:
            additionalDetails = tavily_search(url_data["url"]["title"] + " Give me a json data for this, This json will contains founders,co_investors,team_size,portfolio_acquisition: in details of portfolio,portfolio_unicorns: in details of unicorns,stages_of_entry_investment,sectors_of_investment")
            myJson = json.loads(additionalDetails["response"])
            collection.update_one({'_id': inserted_id}, {'$set': {
                'founders': myJson["founders"],
                'co_investors': myJson["co_investors"],
                'team_size': myJson["team_size"],
                'portfolio_acquisitions': myJson["portfolio_acquisitions"],
                'portfolio_unicorns': myJson["portfolio_unicorns"],
                'stages_of_entry_investment': myJson["stages_of_entry_investment"],
                'sectors_of_investment': myJson["sectors_of_investment"]
            }})

        # Return a JSON response with the inserted_id
        return jsonify({'inserted_id': str(inserted_id)})

    except Exception as error:
        return f"Error: {str(error)}"




@app.route("/update",methods=["GET"])
def update():
    return {"result":"Connected"}


@app.route('/health', methods=["GET"])
def health():
    return {"status" : 200, "message" : "Service Running Successfully"}
if __name__ == '__main__':
    # Run the Flask application
    app.run(debug=True,port=8080,host='0.0.0.0')
