from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
from pymongo import MongoClient
import openai
import anthropic
import json
import re
from tavily import TavilyClient
import collections.abc
from functools import partial
from urllib.parse import urlencode
import requests
from geopy.exc import ConfigurationError, GeocoderQueryError
from geopy.geocoders.base import _DEFAULT_USER_AGENT, DEFAULT_SENTINEL, Geocoder
from geopy.location import Location
from geopy.util import logger
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from bson.json_util import dumps
from dotenv import load_dotenv
import os
load_dotenv()
tavily = TavilyClient(api_key=os.getenv("TAVILYCLIENT_SECRECTID"))
openai.api_key = os.getenv("OPEN_AI_APIKEY")
def scrapDataFromWeb(url_data):
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb+srv://devpdhanasekar:VRBpMHku36ashoCe@cluster0.upee9tc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
        print(client.list_database_names())
        db = client['crafy_db']
        print("Hello")
        collection = db['investment_funds']
        print("Hello")
        # Check if the data already exists
        website_url = url_data["url"]["website"]
        print(website_url)
        print("Hello")
        isAvailable = collection.find_one({"website": website_url})
        
        if isAvailable:
            return {"message": "Data already exists"}

        raw_data = scrape_text_from_urls(website_url)
        tavily_search_result = tavily_qna_search(url_data["url"]["title"] + "company details which contains the social media links and and fund details, investors details,portfolio companies")
        finalResult = claudeCommunication(raw_data+tavily_search_result["response"])
        finalResult = json.loads(finalResult)

        data = {
            'fund_name': finalResult.get("Fund Name", url_data["url"]["title"]),
            'brief_description': finalResult.get("Brief Description", ""),
            'hq_location': finalResult.get("HQ Location", ""),
            'investor_type': finalResult.get("Investor Type",url_data["url"]["type"] if "type" in url_data['url'] else ""),
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
            'founded_year': finalResult.get("Founded Year", ""),
            'team_size': finalResult.get("Team Size", ""),
            'group_email_id_email_id': finalResult.get("Group Email ID/ Email ID", ""),
            'contact_number': url_data['url']["phone"] if "phone" in url_data['url'] else "",
            'linkedin': finalResult.get("LinkedIn", ""),
            'twitter': finalResult.get("Twitter", ""),
            'youtube': finalResult.get("Youtube", ""),
            'co_investors': finalResult.get("Co-Investors", ""),
            'founders': finalResult.get("Founders", ""),
            'tags_keywords': finalResult.get("tags", ""),
            'program_link': finalResult.get("program_link", ""),
            'fund_manager': finalResult.get("fund manager", "")
        }

        inserted_id = collection.insert_one(data).inserted_id
        
        fundSize = tavily_search(url_data["url"]["title"] + " twitter profile")
        results = fundSize["response"]["results"]
        print(results)
        for result in results:
            if "twitter" in result["url"]:
                print(result["url"])
                collection.update_one({'_id': inserted_id}, {'$set': {'twitter': result["url"]}})

        founderLinkedIn = tavily_search(url_data["url"]["title"] + " linkedin profile")
        for result in founderLinkedIn["response"]["results"]:
            if "linkedin" in result["url"]:
                print(result["url"])
                collection.update_one({'_id': inserted_id}, {'$set': {'linkedin': result["url"]}})
                break
        youtubeResults = tavily_search(url_data["url"]["title"] + " youtube chennal link")
        for result in youtubeResults["response"]["results"]:
            if "youtube" in result["url"]:
                print(result["url"])
                collection.update_one({'_id': inserted_id}, {'$set': {'youtube': result["url"]}})
                break
        return jsonify({'inserted_id': str(inserted_id)})

    except Exception as error:
        return f"Error: {str(error)}"


def getFounderLinkedIn(query, location="United States"):
    url = "https://serpapi.com/search"
    
    # Define the parameters for the API request
    params = {
        "engine": "google",
        "q": query,
        "location": location,
        "num": 1,  # Request only the top result
    "api_key": os.getenv("SERP_API_KEY")
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


def tavily_search(query):
    try:
        url = "https://api.tavily.com/search"
        # url = request.get_json()
        qna_response = tavily.search(query=query)
        return{"response":qna_response}
    except Exception as e:
        return f"Error: {str(e)}"

def tavily_qna_search(query):
    try:
        url = "https://api.tavily.com/search"
        # url = request.get_json()
        qna_response = tavily.qna_search(query=query)
        return{"response":qna_response}
    except Exception as e:
        return f"Error: {str(e)}"
    
def scrape_fund_data(url):
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve the web page. Status code: {response.status_code}")
        return None
    soup = BeautifulSoup(response.content, 'html.parser')
    text_data = soup.get_text(separator='\n', strip=True)
    return text_data


def process_with_openai(prompt):
    print("called")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use the new model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        print(response)
        # The 'choices' object structure has changed in the new version
        print(response['choices'][0]['message']['content'].strip())
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(e)
        return f"Error: {str(e)}"



from collections import Counter
def getGoogleMapData(url):

    try:
        print("url",url)
        api_key = "ed386f4e0d0933422e95e5cc1d36f10646b29ede50a22c28c390a905fc0d1af8"  # Replace with your actual SerpApi key
        print(api_key)
        location = url["location"]
        print(location)
        query = url["query"]
        print(query)
        pagination_count = url["pageCount"] * 20
        print(pagination_count)    
        lat, long = get_lat_long(location)
        print(lat, long)

        results = scrape_google_maps(api_key, query, pagination_count, lat, long)
        print("results",results)
        data = parse_results(results)
        seen = set()
        unique_results = []
        
        for result in results:
            # Convert the JSON object to a string with sorted keys to ensure consistency
            result_str = json.dumps(result, sort_keys=True)
            if result_str not in seen:
                seen.add(result_str)
                unique_results.append(result)
        print("adfasdfasdfsa",len(unique_results))
        
        return results
    except Exception as error:
        print(error)
        return []


def get_lat_long(location):
    print("map_called")
    geolocator = Nominatim(user_agent="my_app")
    
    try:
        # Attempt to geocode the location
        location_info = geolocator.geocode(location)
        print(location_info)
        if location_info:
            latitude = location_info.latitude
            longitude = location_info.longitude
            return {latitude, longitude}
        else:
            return "Location not found"
    
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        return f"Error: {str(e)}"



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


def update_founder_data(payload, content_key):
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb+srv://devpdhanasekar:VRBpMHku36ashoCe@cluster0.upee9tc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
        db = client['crafy_db']
        collection = db['investment_funds']

        isFlage = payload.get("isFlage", False)
        
        # If isFlage is True, handle based on context
        if isFlage:
            context = payload.get('context', None)
            base_url = payload.get('base_url', None)
            name = payload.get('name', None)

            if not context or not base_url or not name:
                return {"status": "error", "message": "Missing required fields: 'context', 'base_url', or 'name'"}
            
            # For fundsize
            elif context == "fundsize":
                prompt = f"""
                    What is the overall fund size for {name} organisation?
                    The objective is to return the overall fund size in a clear format.
                    Example response:
                    "Fund VI (2021 onwards) - $290M, Size of the Fund: $1.5 to $3M (₹12 to 24 crs), 12-20% stake"
                """
                resultData = tavily_search(prompt)
                if resultData and 'response' in resultData:
                    fundsize = resultData['response']["results"][0]['content']
                    collection.update_one({'website': base_url}, {'$set': {'fundsize': fundsize}})
                else:
                    return {"status": "error", "message": "Failed to fetch fundsize"}

            # For deals_in_last_12_months
            elif context == "deals_in_last_12_months":
                prompt = f"""
                    What are the funding deals made in the last 12 months by {name} organisation?
                    The objective is to return the deals in a list format.
                    Example response:
                    "Deals in last 12 months: Atomicwork, Flash, DPDzero, Zivy, PicoXpress, Bambrew, SuperK, Optimo Capital, Interview Kickstart"
                """
                resultData = tavily_search(prompt)
                if resultData and 'response' in resultData:
                    deals = resultData['response']["results"][0]['content']
                    collection.update_one({'website': base_url}, {'$set': {'deals_in_last_12_months': deals}})
                else:
                    return {"status": "error", "message": "Failed to fetch last deals"}

            # For team_size
            elif context == "team_size":
                prompt = f"""
                    What is the team size of {name} organisation?
                    The objective is to return the team size as a single number.
                    Example response:
                    "Team Size: 46"
                """
                resultData = tavily_search(prompt)
                if resultData and 'response' in resultData:
                    team_size = resultData['response']["results"][0]['content']
                    collection.update_one({'website': base_url}, {'$set': {'team_size': team_size}})
                else:
                    return {"status": "error", "message": "Failed to fetch team size"}

            # For equity_or_debt
            elif context == "equity_debt_fund_category":
                prompt = f"""
                    Is {name} organisation focused on equity or debt in the investment point of view?
                    The objective is to return 'Equity' or 'Debt' based on their focus.
                    Example response:
                    "Equity"
                """
                resultData = tavily_search(prompt)
                if resultData and 'response' in resultData:
                    equity_or_debt = resultData['response']["results"][0]['content']
                    collection.update_one({'website': base_url}, {'$set': {'equity_debt_fund_category': equity_or_debt}})
                else:
                    return {"status": "error", "message": "Failed to fetch equity_debt_fund_category"}

            # For sector_of_investment
            elif context == "sectors_of_investment":
                prompt = f"""
                    What are the sectors of investment for {name} organisation?
                    The objective of you is to return the sectors of investment in a clear and concise format.
                    Example response: 
                    "Healthcare, FinTech, SaaS, Deep Tech, Media, B2B Services, Consumer Tech, AI Tech, etc."
                """
                resultData = tavily_search(prompt)
                print(resultData)
                if resultData and 'response' in resultData:
                    sectors = resultData['response']["results"][0]['content']
                    collection.update_one({'website': base_url}, {'$set': {'sectors_of_investment': sectors}})
                else:
                    return {"status": "error", "message": "Failed to fetch sector_of_investment"}

            # For funded_year
            elif context == "funded_year":
                prompt = f"""
                    When was {name} organisation founded?
                    The objective of you is to return the founding year in a concise manner.
                    Example response: 
                    "2011"
                """
                resultData = tavily_search(prompt)
                if resultData and 'response' in resultData:
                    funded_year = resultData['response']["results"][0]['content']
                    collection.update_one({'website': base_url}, {'$set': {'funded_year': funded_year}})
                else:
                    return {"status": "error", "message": "Failed to fetch funded_year"}

            # For operating_status
            elif context == "operating_status":
                prompt = f"""
                    What is the operating status of {name} organisation?
                    The objective of you is to return the operating status clearly.
                    Example response: 
                    "Active" or "Inactive"
                """
                resultData = tavily_search(prompt)
                if resultData and 'response' in resultData:
                    operating_status = resultData['response']["results"][0]['content']
                    collection.update_one({'website': base_url}, {'$set': {'operating_status': operating_status}})
                else:
                    return {"status": "error", "message": "Failed to fetch operating_status"}


            elif context == "linkedin":
                linkedin_result = tavily_search(f'{name} linkedin profile')
                if linkedin_result and 'response' in linkedin_result:
                    for result in linkedin_result["response"].get("results", []):
                        if "linkedin" in result["url"]:
                            collection.update_one({'website': base_url}, {'$set': {'linkedin': result["url"]}})
                            break
                    else:
                        return {"status": "error", "message": "No LinkedIn profile found"}
                else:
                    return {"status": "error", "message": "Failed to fetch LinkedIn profile"}

            elif context == "youtube":
                youtube_result = tavily_search(f'{name} youtube channel link')
                if youtube_result and 'response' in youtube_result:
                    for result in youtube_result["response"].get("results", []):
                        if "youtube" in result["url"]:
                            collection.update_one({'website': base_url}, {'$set': {'youtube': result["url"]}})
                            break
                    else:
                        return {"status": "error", "message": "No YouTube channel found"}
                else:
                    return {"status": "error", "message": "Failed to fetch YouTube channel"}
            elif context == "twitter":
                youtube_result = tavily_search(f'{name} twitter profile link')
                print(youtube_result)
                if youtube_result and 'response' in youtube_result:
                    for result in youtube_result["response"].get("results", []):
                        if "twitter" in result["url"]:
                            collection.update_one({'website': base_url}, {'$set': {'twitter': result["url"]}})
                            break
                    else:
                        return {"status": "error", "message": "No twitter channel found"}
                else:
                    return {"status": "error", "message": "Failed to fetch twitter channel"}

            return {"status": "success", "message": "Data updated successfully"}

        # Handle web scraping if isFlage is False
        else:
            website_url = payload.get("url", None)
            base_url = payload.get("base_url", None)

            if not website_url or not base_url:
                return {"status": "error", "message": "Missing 'url' or 'base_url'"}

            isAvailable = collection.find_one({"website": base_url})
            if isAvailable:
                rawData = scrape_fund_data(website_url)

                if content_key == "portfolio_companies":
                    prompt = create_prompt(rawData, content_key)
                    updated_content = process_with_openai(prompt)
                    if updated_content:
                        companies = updated_content.split(',')
                        collection.update_one({"website": base_url}, {"$set": {content_key: updated_content}})
                        collection.update_one({"website": base_url}, {"$set": {"no_of_portfolio_companies_invested_in": len(companies)}})
                        return {"status": "success", "message": "Portfolio companies updated successfully"}
                    else:
                        return {"status": "error", "message": "Failed to update portfolio companies"}

                elif content_key == "portfolio_exits":
                    prompt = create_prompt(rawData, content_key)
                    updated_content = process_with_openai(prompt)
                    if updated_content:
                        companies = updated_content.split(',')
                        collection.update_one({"website": base_url}, {"$set": {content_key: updated_content}})
                        collection.update_one({"website": base_url}, {"$set": {"no_of_exits": len(companies)}})
                        return {"status": "success", "message": "Portfolio exits updated successfully"}
                    else:
                        return {"status": "error", "message": "Failed to update portfolio exits"}

                elif content_key == "description":
                    prompt = create_prompt(rawData, content_key)
                    updated_content = process_with_openai(prompt)
                    if updated_content:
                        collection.update_one({"website": base_url}, {"$set": {content_key: updated_content}})
                        return {"status": "success", "message": "Description updated successfully"}
                    else:
                        return {"status": "error", "message": "Failed to update description"}

                else:
                    prompt = create_prompt(rawData, content_key)
                    updated_content = process_with_openai(prompt)
                    if updated_content:
                        collection.update_one({"website": base_url}, {"$set": {content_key: updated_content}})
                        return {"status": "success", "message": f"{content_key} updated successfully"}
                    else:
                        return {"status": "error", "message": f"Failed to update {content_key}"}
            else:
                return {"status": "error", "message": "Website not found in the database"}

    except Exception as error:
        return {"status": "error", "message": str(error)}

# Helper function to create a prompt
def create_prompt(rawData, content_key):
    prompt = f"""
    {rawData}
    The objective of you is to create a complete and accurate string output based on the web-scraped details stored in the variable webScarp. The string output should fill the provided in the template with relevant information extracted from webScarp. The goal is to generate a comprehensive and informative string representation of user context that are mentioned below.
    User context is {content_key}.
    Follow the same format and structure as shown in the example for {content_key}.
    """
    return prompt

def updateFounderDataManual(payload, content_key):
    try:
        client = MongoClient('mongodb+srv://devpdhanasekar:VRBpMHku36ashoCe@cluster0.upee9tc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
        db = client['crafy_db']
        collection = db['investment_funds']
        isAvailable = collection.find_one({"website": payload["base_url"]})
        
        print(isAvailable)
        if isAvailable:
               collection.update_one(
                {"website": payload["base_url"]},
                {"$set": {content_key: payload["user_answer"]}}
            )
               return "Updated successfully"

    except Exception as error:
        return str(error)
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
        return response
    except Exception as e:
        return f"Error: {str(e)}"
    

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
def get_all_endpoints_with_base(url):
    try:
        # Send a request to the base URL
        response = requests.get(url, verify=False)
        response.raise_for_status()  # Ensure we catch HTTP errors
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return set()  # Return an empty set in case of error

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all <a> tags with href attributes and resolve full URLs
    endpoints = {urljoin(url, link['href']) for link in soup.find_all('a', href=True)}

    return endpoints

def is_valid_endpoint(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

def fetch_page_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def scrape_text_from_urls(base_url):
    try:
    # Get all endpoints with the base URL
        print("Base URL:")
        endpoints = get_all_endpoints_with_base(base_url)
        print("Endpoints:", endpoints)
        
        # Prepare the prompt
        prompt = f"""
        I have a list of URLs related to {base_url}. I need to identify and return only the high-priority valid URLs from this list. High-priority URLs include main website, portfolio companies, news, press releases, reports, resources, and key contact information. Here is the list of URLs:
        {endpoints}
        Please return only the high-priority valid URLs from the provided list. Return a response in list format.
        The response should be in the following format: [urls]
        """
        
        # Process with OpenAI
        result = process_with_openai(prompt)
        start = result.find("[")
        end = result.find("]")
        result = result[start:end+1]
        print("Result:", type(result))
        
        # Parse the response
        try:
            url_list = json.loads(result.replace("'", '"'))  # Ensure it's in valid JSON format
        except json.JSONDecodeError:
            print("Error decoding JSON response:", result)
            url_list = []
        
        print("High-priority URLs:", url_list)
        
        # Initialize a list to store all text data
        all_text_data = []

        # Scrape data from high-priority URLs
        for url in url_list:
            print(f"Fetching data from {url}...")
            page_content = fetch_page_content(url)
            if page_content:
                soup = BeautifulSoup(page_content, 'html.parser')
                # Extract text from the page
                page_text = soup.get_text(separator='\n', strip=True)
                all_text_data.append(page_text)
        
        # Aggregate all text data
        aggregated_text = "\n\n".join(all_text_data)
        
        # Print the aggregated text or save it to a file
        print("Aggregated Text Data:")
        print(aggregated_text)  # Print the first 2000 characters for preview
        with open("aggregated_text_data.txt", "w", encoding="utf-8") as file:
            file.write(aggregated_text)
        return aggregated_text
    except Exception as e:
        print(f"Error occurred: {e}")
        return None

import anthropic
import os


def aiChatbot(raw_data):
    # Initialize the Claude client using the API key
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_APIKEY")  # Replace with your actual API key
    )

    # Prepare the conversation payload using the Messages API format
    messages = raw_data
    content = messages[len(messages)-1]["content"]
    tavily_result = tavily_qna_search(content)
    print(tavily_result)

    try:
        # Send the conversation to Claude's Messages API
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",  # The correct model for the Messages API
            messages=messages,
            max_tokens=4096,
            stop_sequences=[anthropic.HUMAN_PROMPT],  # Optional, customize if needed
        )
        print(response.content[0].text)
        return {"assistant":response.content[0].text+" "+tavily_result["response"]}
    
    except Exception as e:
        # Handle any exceptions that occur during the API call
        print(f"Error communicating with Claude: {e}")
        return "Sorry, there was an issue processing your request."
    
def claudeCommunication(raw_data):
    client = anthropic.Anthropic(
        # Use an environment variable for the API key
        api_key=os.getenv("ANTHROPIC_APIKEY")
    )
    
    # Use triple quotes for the prompt to avoid formatting issues
    prompt = f"""
You are tasked with creating a complete and accurate JSON output based on web-scraped details about a company. Your goal is to fill all the keys in the provided JSON template with relevant information extracted from the web-scraped data. Follow these instructions carefully:

1. First, you will be provided with web-scraped details about a company in the following format:

<web_scrape>
{raw_data}
</web_scrape>

2. You will also be given a JSON template to fill. The template looks like this:

<json_template>
{{
  "Fund Name": "Blume Ventures",
  "Brief Description": "Blume is an early stage venture fund that backs startups with both funding as well as active mentoring. We typically invest in tech-led startups, led by founders who are obsessed with solving hard problems, uniquely Indian in nature, and impacting large markets. Our vision is to be the leading platform that sources, funds, nurtures and creates value for India's brightest young startups – helping them 'blume'!",
  "HQ Location": "Mumbai",
  "Investor Type": "Venture Capital",
  "Equity / Debt (Fund Category)": "Equity",
  "Stages of Entry/ Investment": ["Early Stage", "Growth stage", "IPO", "Unicorn"],
  "Sectors of Investment": [
    "60-65% of the new fund in domestic-heavy sectors such as healthcare, financial services, commerce and brands, jobs and education, and digital media and gaming. The other 35-40% of the fund will focus on SaaS, and DeepTech (including CleanTech, manufacturing, blockchain) companies, typically in B2B",
    "EV & Mobility",
    "ClimateTech",
    "B2B Services",
    "SMB",
    "SaaS",
    "Media",
    "Entertainment & Gaming",
    "Consumer Tech",
    "Ari Tech",
    "Artificial Intelligence",
    "B2B Commerce and Marketplaces",
    "Consumer Brands",
    "Consumer Services",
    "Commerce Enabler",
    "Consumer Tech",
    "Deep Tech",
    "Ed Tech",
    "Fin Tech",
    "Food Tech",
    "HR Tech",
    "Healthcare",
    "ITSM",
    "Infrastructure Saas and Dev Tools",
    "Logistics",
    "Real Estate",
    "Sustainability"
  ],
  "Geographies Invested In": ["Bengaluru", "Chennai", "Hyderabad", "Mumbai", "Vijayawada", "Delhi NCR", "Pune", "Singapore", "UK", "Canada", "UAE", "USA"],
  "Portfolio Companies": ["Jai Kisan", "Niqo Robotics", "Stellapps", "Atomic Work", "Aerem", "ApnaKlub", "Bambrew", "Cashify", "Classplus", "Manufactured", "Procol", "Spinny", "Battery Smart", "BHIVE Workspace", "Dunzo", "E2E Networks", "Ethereal Machines", "Exotel", "Finvolv", "Futwork", "HealthAssure", "IDfy", "Infollion", "InTouchApp", "Kaliedofin", "LeadCandy", "Leverage Edu", "Printo", "Qyuki", "Redquanta", "Rocketium", "Routematic", "Runnr", "Smartstaff", "SquadStack", "THB", "Tricog", "Tripvillas", "WebEngage", "Yulu", "Zip Dial", "Zopper", "Ati Motors", "Carbon Clean", "ElectricPe", "Euler Motors", "Vecmocon Technologies", "Flash", "Freakins", "LLB", "Milkbakset", "Promptec", "Purplle", "SuperK", "Ultrahuman", "DataWeave", "Futwork", "Instamojo", "LoveLocal", "NowFloats", "Snapbizz", "The Wedding Brigade", "Uniqode", "BillBachao", "HealthifyMe", "IntrCity", "Leverage Edu", "Medfin", "Multipl", "Slice", "smallcase", "Stage 3", "Trip Villas", "Unacademy", "Unocoin", "Uolo", "Virohan", "Accio", "Adepto", "AutoVerse", "BeatO", "Glamrs", "iService", "Koo", "Stage", "Taaraka", "WeAreHolidays", "Wiom", "Agara Labs", "GreyOrange", "Locus", "Pixxel", "Systemantics", "Tookitaki", "Tricog", "Zenatix", "Taxiforsure", "Alippo", "Classplus", "Mastree", "Mockbank", "Oheyo", "Virohan", "Bluecopa", "Bureau", "Chaitanya", "Chillr", "Clink", "DPDZero", "Finvolv", "Moneysights", "Mysa", "Optimo", "PrivateCircle", "Qubecell", "Servify", "Turtlemint", "Zoppor", "ChefKart", "GreyHR", "Interview Kickstart", "Mettl", "Rizort", "Skillenza", "Smartstaff", "Superset", "TapChief", "HealthAssure", "Hybrent", "Karmic", "Ultrahuman", "1Click", "Frambench", "InTouchApp", "LambdaTest", "Minjar", "Scribble Data", "Sift Hub", "Sprinto", "Uniqode", "Zapccale", "Zipy", "Atomicwork", "Patch", "Sprinto", "Valgen", "Pico Xpress", "Hashcube", "Koo", "MechMocha", "Rolocule", "Stage", "StrmEasy", "Salty", "Fastfox", "Hotelogix", "Hybrent", "Threadsol", "Wiz Commerce"],
  "No. of Portfolio Companies Invested in": 160,
  "No. of Exits": 39,
  "Portfolio Acquisitions": ["Agara Labs", "Chillr", "Hybrent", "Mettl", "Minjar", "Promptec", "Runnr", "Superset", "Taxi for sure", "Threadsol", "ZipDial", "1click", "Bill Bachao", "Chaitanya", "Framebench", "iService", "Mastree", "MilkBasket", "Nowfloats", "Qubecell", "StrmEasy", "TapChief", "Zenatix", "Adepto", "Clink (Gharpay)", "Fastfox", "Glamrs", "Karmic", "LBB", "MechMocha", "MockBank", "Moneysights", "Patch", "Rolocule", "Valgen Infosys", "We are Holidays"],
  "Website": "https://blume.vc/",
  "Portfolio Unicorns / Soonicorns": ["Spinny", "Purplle", "slice", "Unacademy"],
  "Portfolio Exits": ["Agara Labs", "Chillr", "E2E Networks", "Hybrent", "Infollion", "Mettl", "Minjar", "Promptec", "Runnr", "Superset", "Taxi for sure", "Threadsol", "Uniqode", "ZipDial", "1click", "Bill Bachao", "Chaitanya", "Framebench", "iService", "Mastree", "MilkBasket", "Nowfloats", "Qubecell", "StrmEasy", "TapChief", "Zenatix", "Adepto", "Clink (Gharpay)", "Fastfox", "Glamrs", "Karmic", "LBB", "MechMocha", "MockBank", "Moneysights", "Patch", "Rolocule", "Valgen Infosys", "We are Holidays"],
  "Operating Status": "Active",
  "Deals in last 12 months": ["Atomicwork", "Flash", "DPDzero", "Zivy", "PicoXpress", "Bambrew", "SuperK", "Optimo Capital", "Interview Kickstart"],
  "AUM (Doller)": "Fund VI (2021 onwards) - $290M",
  "Size of the Fund": "$1.5 to $3M (₹12 to 24 crs), 12-20% stake",
  "Founded Year": 2011,
  "Team Size": 46,
  "Group Email ID/ Email ID": "contact@blume.vc",
  "Contact Number": "022-43471659",
  "LinkedIn": "https://www.linkedin.com/company/blume-venture-advisors/?originalSubdomain=in",
  "Twitter (X)": "https://x.com/blumeventures",
  "Youtube": "https://www.youtube.com/channel/UCMVGOgVL6OJyoxWFN1pmLCw",
  "Instagram": "",
  "Founders": ["Sanjay Nath", "Karthik Reddy"],
  "tags":[],
  "program link":""
}}
</json_template>

3. Analyze the web-scraped details:
   - Carefully read through the web_scrape data.
   - Identify information that corresponds to each key in the JSON template.
   - Pay attention to both explicit mentions (e.g., "Founded in 2010") and implicit information that can be inferred from the context.

4. Fill the JSON template:
   - For each key in the JSON template, find the corresponding information in the web_scrape data.
   - If you find an exact match or highly relevant information, use it to fill the key.
   - If the information is not explicitly stated but can be reasonably inferred, make a logical inference and use it.
   - Ensure that all keys are filled with accurate and relevant information.

5. Handling missing information:
   - If you cannot find information for a specific key, do not leave it empty.
   - Instead, use one of the following placeholder values:
     - "Not specified" if the information is not mentioned at all.
     - "Not applicable" if it's clear that the field doesn't apply to this company.
     - "Unknown" if the information should exist but is not provided in the web_scrape data.

6. Formatting the output:
   - Present your final output as a complete JSON object.
   - Ensure that all keys from the original template are included.
   - Use double quotes for both keys and string values.
   - Separate key-value pairs with commas.
   - Enclose the entire JSON object in curly braces.

7. Final check:
   - Review your JSON output to ensure all keys are filled.
   - Verify that the information accurately represents the data from the web_scrape.
   - Make sure the JSON is properly formatted and valid.

Provide your complete JSON output inside <json_output> tags. Do not include any explanations or comments outside of these tags.
"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=4096,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    print(message.content[0].model_dump_json)
    json_content = claude_response_to_json(message.content)
    print(json_content)
    return json_content



def claude_response_to_json(response):
    # Check if response is a list of TextBlock objects
    if isinstance(response, list) and all(hasattr(item, 'text') for item in response):
        # Concatenate all text fields
        full_text = ' '.join(item.text for item in response)
    elif isinstance(response, str):
        full_text = response
    else:
        raise ValueError("Invalid input type. Expected string or list of TextBlock objects.")

    # Extract JSON content from between <json_output> tags
    json_match = re.search(r'<json_output>(.*?)</json_output>', full_text, re.DOTALL)
    
    if not json_match:
        raise ValueError("No JSON content found between <json_output> tags")
    
    json_string = json_match.group(1).strip()
    
    # Parse the JSON string
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {str(e)}")
    
    # Format the JSON with indentation
    formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
    
    return formatted_json