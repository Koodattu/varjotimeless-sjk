from flask import Flask, request, jsonify

app = Flask(__name__)

# Global in-memory storage for transcriptions
transcription_store = ""

@app.route("/transcription", methods=["POST"])
def receive_transcription():
    global transcription_store
    data = request.get_json()
    # Expecting JSON payload: { "text": "the transcribed text..." }
    new_text = data.get("transcription", "").strip()
    if new_text:
        transcription_store += new_text + " "
        print(f"Updated transcription store: {transcription_store}")
        return jsonify({"status": "OK", "message": "Transcription stored."}), 200
    else:
        return jsonify({"status": "Error", "message": "No transcription provided."}), 400

@app.route("/transcription", methods=["GET"])
def get_transcription():
    # Optional endpoint to retrieve the full transcription so far.
    return jsonify({"transcription": transcription_store}), 200

if __name__ == "__main__":
    # Run the server on all interfaces at port 5000
    app.run(host="0.0.0.0", port=6000, debug=True)
