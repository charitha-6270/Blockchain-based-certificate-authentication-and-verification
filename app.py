import os
import json
import hashlib
from flask import Flask, render_template, request
from web3 import Web3
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

INFURA_URL = os.getenv("INFURA_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# Blockchain connection
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
if not w3.is_connected():
    raise Exception("❌ Web3 not connected. Check INFURA_URL.")

with open("contract_abi.json", "r") as f:
    contract_abi = json.load(f)

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

# Flask app
app = Flask(__name__)

# --- FIX: absolute path for uploads ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

REGISTER_PASSWORD = "admin123"  # Password required for issuers

# --- Helper functions ---
def file_hash(file_path):
    """Compute SHA256 hash of a file and return as bytes32"""
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    # sha256 → hex → bytes32
    return Web3.to_bytes(hexstr=hashlib.sha256(file_bytes).hexdigest())

def save_issuer_details(cert_id, cert_hash, issuer, timestamp):
    """Save certificate issuer details locally in JSON"""
    issuer_data = {
        "id": cert_id,
        "hash": cert_hash.hex(),
        "issuer": issuer,
        "timestamp": timestamp
    }

    if not os.path.exists("issuers.json"):
        with open("issuers.json", "w") as f:
            json.dump([], f)

    with open("issuers.json", "r+") as f:
        data = json.load(f)
        data.append(issuer_data)
        f.seek(0)
        json.dump(data, f, indent=4)

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        password = request.form.get("password")
        if password != REGISTER_PASSWORD:
            return "❌ Invalid password. Access denied."

        file = request.files["certificate"]
        if file:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            # Compute hash (bytes32)
            cert_hash = file_hash(file_path)

            # Check if certificate already exists
            exists, _, _, _ = contract.functions.verifyCertificate(cert_hash).call()
            if exists:
                return "❌ Certificate already registered!"

            # Build and send transaction
            nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
            txn = contract.functions.registerCertificate(cert_hash).build_transaction({
                "from": ACCOUNT_ADDRESS,
                "nonce": nonce,
                "gas": 300000,
                "gasPrice": w3.to_wei("15", "gwei")
            })

            signed_txn = w3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)  

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            # Get certificate count from contract
            cert_id = contract.functions.certificateCount().call()
            save_issuer_details(cert_id, cert_hash, ACCOUNT_ADDRESS, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            return f"✅ Certificate registered! Tx: {tx_hash.hex()}"

    return render_template("register.html")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        file = request.files["certificate"]
        if file:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            cert_hash = file_hash(file_path)

            exists, cert_id, issuer, timestamp = contract.functions.verifyCertificate(cert_hash).call()

            return render_template(
                "result.html",
                exists=exists,
                cert_id=cert_id,
                issuer=issuer,
                timestamp=datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if timestamp else None
            )

    return render_template("verify.html")

if __name__ == "__main__":
    app.run(debug=True)



