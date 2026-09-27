import logging
import httpx#httpx is used to send HTTP requests asynchronously to Supabase.
import json#Used to convert Python objects into JSON and JSON back into Python objects.
from datetime import datetime, timezone#Used for type hints. It tells us what type of data a variable/function expects or returns.
from typing import List, Optional, Dict

logger = logging.getLogger('ats_resume_scorer')#Creates a logger named ats_resume_scorer.

#This imports the Supabase URL and key that you stored in your configuration / .env.
from backend.core.config import SUPABASE_URL, SUPABASE_KEY

def _get_headers():  #This function prepares the HTTP headers required to communicate with Supabase.
    if not SUPABASE_URL or not SUPABASE_KEY:  #If the Supabase URL or key is missing, it returns None.
        return None
    #Sends your Supabase API key with the request.
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",#Provides the key as a Bearer token for authorization.
        "Content-Type": "application/json",#"The data I'm sending is JSON."
        "Prefer": "return=representation" #Tells Supabase to return the inserted record after successfully inserting it.
    }

#This is the main function.
#It saves the resume analysis into Supabase.
async def save_analysis(user_id: str, filename: str, analysis_result: Dict) -> Optional[str]:
    #Calls the previous function to prepare Supabase headers.
    headers = _get_headers()
    if not headers:#If credentials aren't available, stop.
        return None

    def _json_default(o):#This is a helper function used when Python encounters an object that JSON doesn't normally understand.
        if hasattr(o, 'model_dump'):#If the object is a Pydantic model, model_dump() converts it into a normal Python dictionary.
            return o.model_dump()#It converts the object into a string.
        return str(o)
    serializable_result = json.loads(json.dumps(analysis_result, default=_json_default))#This basically converts the analysis result into clean JSON-compatible Python data.


     #Creating the database document
     #This creates the data that will be inserted into your Supabase table
    doc = {
        "user_id": user_id,
        "filename": filename,
        "ats_score": serializable_result.get("ats_score", 0),
        "keyword_match": serializable_result.get("keyword_match", 0),
        "missing_keywords": serializable_result.get("missing_keywords", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_result": serializable_result,
    }


    #Creating Supabase REST API URL
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"#This creates the URL for your Supabase table.analyse is a table in supebase postgree db and rest/v1 is the REST API
    #Sending data to Supabase inside using try catch block
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=doc)#json=doc means your doc dictionary is sent as JSON.
            response.raise_for_status()#If Supabase returns an HTTP error such as:400,401,500,403
            data = response.json()#Converts Supabase's JSON response into Python data.
            if data and len(data) > 0:
                inserted_id = str(data[0].get("id"))#Gets the id of the newly inserted analysis.
                logger.info(f"Saved analysis for user {user_id}: {inserted_id}")
                return inserted_id
            return None
    except Exception as exc:
        logger.error(f"Failed to save analysis to Supabase: {exc}")
        if 'response' in locals():
            logger.error(f"Supabase status: {response.status_code}")
            logger.error(f"Supabase response: {response.text}")
        return None

async def get_user_history(user_id: str) -> List[Dict]:
    headers = _get_headers()
    if not headers:
        return []

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                headers=headers, 
                params={
                    "user_id": f"eq.{user_id}",
                    "order": "created_at.desc"
                }
            )
            response.raise_for_status()
            docs = response.json()
            
            results = []
            for doc in docs:
                results.append({
                    "id": str(doc.get("id")),
                    "filename": doc.get("filename", "resume"),
                    "resume_name": doc.get("filename", "resume"),
                    "job_title": "Software Engineer",
                    "ats_score": doc.get("ats_score", 0),
                    "keyword_match": doc.get("keyword_match", 0),
                    "missing_keywords": doc.get("missing_keywords", []),
                    "date": doc.get("created_at", ""),
                    "created_at": doc.get("created_at", ""),
                    "analysis_result": doc.get("analysis_result", {}),
                })
            return results
    except Exception as exc:
        logger.error(f"Failed to fetch history from Supabase: {exc}")
        return []

async def delete_analysis(analysis_id: str, user_id: str) -> bool:
    headers = _get_headers()
    if not headers:
        return False

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url, 
                headers=headers, 
                params={
                    "id": f"eq.{analysis_id}",
                    "user_id": f"eq.{user_id}"
                }
            )
            response.raise_for_status()
            return True
    except Exception as exc:
        logger.error(f"Failed to delete analysis {analysis_id}: {exc}")
        return False
