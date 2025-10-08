from flask import Flask, request, jsonify
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

app = Flask(__name__)

# ServiceTitan Configuration
ST_CLIENT_ID = "cid.jfxfxq48ex4g3rye0efm6tgrb"
ST_CLIENT_SECRET = "cs1.msccvj18obioj9ou0hvfbqjvl9xpaszo5czh4pigvnzjrj6t8i"
ST_APP_KEY = "ak1.6epj2e965br72tf00nj1fy2nv"
ST_TENANT_ID = "1745774105"

AUTH_URL = "https://auth.servicetitan.io/connect/token"
BASE_URL = "https://api.servicetitan.io"

def get_token() -> str:
    """Get ServiceTitan OAuth token."""
    response = requests.post(
        AUTH_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": ST_CLIENT_ID,
            "client_secret": ST_CLIENT_SECRET,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]

def normalize_phone(phone: str) -> str:
    """Normalize phone to 10 digits."""
    if not phone:
        return ""
    digits = ''.join(c for c in phone if c.isdigit())
    if digits.startswith('1') and len(digits) == 11:
        digits = digits[1:]
    return digits if len(digits) == 10 else ""

def fetch_jobs(token: str, days_back: int) -> List[Dict[str, Any]]:
    """Fetch jobs from ServiceTitan."""
    headers = {
        "Authorization": f"Bearer {token}",
        "ST-App-Key": ST_APP_KEY,
    }

    cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

    all_jobs = []
    page = 1

    while True:
        response = requests.get(
            f"{BASE_URL}/jpm/v2/tenant/{ST_TENANT_ID}/jobs",
            headers=headers,
            params={
                "createdOnOrAfter": cutoff_date,
                "page": page,
                "pageSize": 500,
            },
        )
        response.raise_for_status()
        data = response.json()

        jobs = data.get("data", [])
        if not jobs:
            break

        all_jobs.extend(jobs)

        if not data.get("hasMore", False):
            break

        page += 1
        time.sleep(0.1)

    return all_jobs

def fetch_estimates(token: str, job_id: int) -> List[Dict[str, Any]]:
    """Fetch estimates for a job."""
    headers = {
        "Authorization": f"Bearer {token}",
        "ST-App-Key": ST_APP_KEY,
    }

    response = requests.get(
        f"{BASE_URL}/sales/v2/tenant/{ST_TENANT_ID}/estimates",
        headers=headers,
        params={"jobId": job_id},
    )
    response.raise_for_status()
    return response.json().get("data", [])

def fetch_customer_contacts(token: str, customer_id: int) -> Dict[str, Any]:
    """Fetch customer contact info."""
    headers = {
        "Authorization": f"Bearer {token}",
        "ST-App-Key": ST_APP_KEY,
    }

    response = requests.get(
        f"{BASE_URL}/crm/v2/tenant/{ST_TENANT_ID}/customers/{customer_id}",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    contacts = data.get("contacts", [])
    phones = []
    emails = []

    for contact in contacts:
        contact_type = contact.get("type", "")
        value = contact.get("value", "")

        if contact_type in ["Phone", "MobilePhone"] and value:
            normalized = normalize_phone(value)
            if normalized:
                phones.append(normalized)
        elif contact_type == "Email" and value:
            emails.append(value)

    return {
        "phones": phones,
        "emails": emails,
    }

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "servicetitan-api"}), 200

@app.route('/sync', methods=['POST'])
def sync_estimates():
    """Main endpoint to sync unsold estimates."""
    try:
        # Get parameters from request
        data = request.get_json() or {}
        days_back = data.get('daysBack', 30)

        # Get token
        token = get_token()

        # Fetch jobs
        jobs = fetch_jobs(token, days_back)

        # Process estimates
        all_unsold = []
        enriched_count = 0

        for job in jobs:
            job_id = job.get("id")
            customer_id = job.get("customerId")

            if not job_id:
                continue

            # Fetch estimates for this job
            estimates = fetch_estimates(token, job_id)
            time.sleep(0.1)

            for est in estimates:
                # Filter for unsold (status = 0)
                if est.get('status', {}).get('value') == 0:
                    created_on = est.get('createdOn', '')
                    created_date = datetime.fromisoformat(created_on.replace('Z', '+00:00'))
                    days_old = (datetime.now().astimezone() - created_date).days

                    estimate_record = {
                        "estimate_id": est.get("id"),
                        "job_id": job_id,
                        "customer_id": customer_id,
                        "name": est.get("name", ""),
                        "total": est.get("total", 0),
                        "status": est.get("status", {}).get("name", ""),
                        "created_on": created_on,
                        "days_old": days_old,
                        "phones": [],
                        "emails": [],
                    }

                    # Enrich with customer contacts
                    if customer_id:
                        try:
                            contacts = fetch_customer_contacts(token, customer_id)
                            estimate_record["phones"] = contacts["phones"]
                            estimate_record["emails"] = contacts["emails"]
                            enriched_count += 1
                            time.sleep(0.1)
                        except Exception:
                            pass

                    all_unsold.append(estimate_record)

        # Return metrics
        total_value = sum(est.get("total", 0) for est in all_unsold)

        return jsonify({
            "success": True,
            "metrics": {
                "jobs_checked": len(jobs),
                "unsold_estimates_found": len(all_unsold),
                "total_value": total_value,
                "enriched_with_contacts": enriched_count,
                "days_back": days_back,
            },
            "estimates": all_unsold
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Railway sets PORT environment variable
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
