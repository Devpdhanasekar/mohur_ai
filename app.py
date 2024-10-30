from flask import Flask, jsonify, request
from flask_cors import CORS
from controllers import initialDataScrapeFromAI,scrapeDataFromGoogleMap,updateDataFromDB,getInvestorsDataFromDB,updateDataFromDBManual,aiChatbotCommunication
app = Flask(__name__)
CORS(app)


@app.route('/initialDataScrape', methods=["POST"])
def initialDataScrape():
    try:
        payloadData = request.get_json()
        print(payloadData)
        response = initialDataScrapeFromAI(payloadData)
        return response
    except Exception as error:
        return jsonify({"message": "Invalid request", "error": str(error)}), 400

@app.route('/googlemap', methods=["POST"])
def getDataFromGoogleMap():
    try:
        payloadData = request.get_json()
        print(payloadData)
        response = scrapeDataFromGoogleMap(payloadData)
        return response
    except Exception as error:
        return jsonify({"message": "Invalid request", "error": str(error)}), 400



@app.route('/update', methods=["POST"])
def updateData():
    try:
        payloadData = request.get_json()
        print(payloadData)
        response = updateDataFromDB(payloadData,payloadData['context'])
        return jsonify({"response":response}),200
    except Exception as error:
        return jsonify({"message": "Invalid request", "error": str(error)}), 400



@app.route('/updateManual', methods=["POST"])
def updateDataManual():
    try:
        payloadData = request.get_json()
        print(payloadData)
        response = updateDataFromDBManual(payloadData,payloadData['context'])
        return jsonify({"response":response}),200
    except Exception as error:
        return jsonify({"message": "Invalid request", "error": str(error)}), 400

@app.route('/investment', methods=["GET"])
def getInvestorData():
    try:
        response = getInvestorsDataFromDB()
        return response,200
    except Exception as error:
        return jsonify({"message": "Invalid request", "error": str(error)}), 400

@app.route('/chatbot', methods=["POST"])
def communicateWithChatbot():
    try:
        payloadData = request.get_json()
        print(payloadData)
        response = aiChatbotCommunication(payloadData["message"])
        return response,200
    except Exception as error:
        return jsonify({"message": "Invalid request", "error": str(error)}), 400

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080,debug=True)