from helpers import scrapDataFromWeb,getGoogleMapData,update_founder_data, getInvestmentData,updateFounderDataManual,aiChatbot
def initialDataScrapeFromAI(payloadData):
    try:
        response = scrapDataFromWeb(payloadData)
        return response
    except Exception as error:
        print("Error while scraping data from AI: ", error)

def scrapeDataFromGoogleMap(payloadData):
    try:
        response = getGoogleMapData(payloadData)
        return response
    except Exception as error:
        print("Error while scraping data from Google Map: ", error)

def updateDataFromDB(payloadData,content):
    try:
        response = update_founder_data(payloadData,content)
        return response
    except Exception as error:
        print("Error while scraping data from Google Map: ", error)



def updateDataFromDBManual(payloadData,content):
    try:
        response = updateFounderDataManual(payloadData,content)
        return response
    except Exception as error:
        print("Error while scraping data from Google Map: ", error)

def getInvestorsDataFromDB():
    try:
        response = getInvestmentData()
        return response
    except Exception as error:
        print("Error while scraping data from Google Map: ", error)

def aiChatbotCommunication(payloadData):
    try:
        response = aiChatbot(payloadData)
        return response
    except Exception as error:
        print("Error while scraping data from Google Map: ", error)