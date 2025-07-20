import logging
import json
import os
import azure.functions as func
from openai import AzureOpenAI

try:
    openai_client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version="2024-02-01"
    )
    logging.info("Azure OpenAI client initialized successfully.")
except KeyError as e:
    logging.error(f"Missing environment variable: {e}. Please ensure AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT are set.")
    openai_client = None # Set to None to handle cases where initialization fails
except Exception as e:
    logging.error(f"Error initializing Azure OpenAI client: {e}")
    openai_client = None


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    if openai_client is None:
        return func.HttpResponse(
            "Azure OpenAI client not initialized. Please check environment variables and function logs.",
            status_code=500
        )

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Please pass a JSON body in the request.",
            status_code=400
        )
    except Exception as e:
        logging.error(f"Error parsing request body: {e}")
        return func.HttpResponse(
            "Error processing request. Ensure valid JSON is provided.",
            status_code=400
        )

    # Extract relevant information from the request body
    # Customize these keys based on your incoming JSON structure
    original_email_subject = req_body.get('subject')
    original_email_body = req_body.get('body')
    sender_name = req_body.get('sender_name')
    recipient_name = req_body.get('recipient_name') # The name of the person receiving the reply (you/your system)
    sender_email = req_body.get('sender_email')

    if not all([original_email_subject, original_email_body, sender_name]):
        return func.HttpResponse(
            "Please provide 'subject', 'body', and 'sender_name' in the request body.",
            status_code=400
        )

    try:
        # Construct the prompt for Azure OpenAI
        # This is where you define how the AI should generate the reply
        prompt_messages = [
            {"role": "system", "content": "You are a helpful assistant that drafts professional email replies. Be concise and polite."},
            {"role": "user", "content": f"The following is an email from {sender_name} (email: {sender_email}) with the subject '{original_email_subject}' and body:\n\n---\n{original_email_body}\n---\n\nDraft a concise and polite reply. Start the reply with 'Dear {sender_name},'"},
        ]

        # Add more context if available, e.g., if you know the recipient's name for the reply
        if recipient_name:
            prompt_messages[1]["content"] += f"\n\nSign off as {recipient_name}."

        logging.info(f"Sending prompt to Azure OpenAI: {prompt_messages}")

        response = openai_client.chat.completions.create(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"], # Your deployment name (e.g., 'gpt-35-turbo-deployment')
            messages=prompt_messages,
            temperature=0.7,  # Controls creativity (0.0-1.0)
            max_tokens=250,   # Max tokens for the reply
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None # You can define stop sequences if needed
        )

        reply_content = response.choices[0].message.content.strip()
        logging.info(f"Generated reply: {reply_content}")

        # You might want to generate a suggested subject for the reply
        # For simplicity, we'll just prefix the original subject for now
        reply_subject = f"Re: {original_email_subject}"

        # Prepare the response to be sent back
        return_payload = {
            "reply_subject": reply_subject,
            "reply_body": reply_content
        }

        return func.HttpResponse(
            json.dumps(return_payload),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error generating reply: {e}")
        return func.HttpResponse(
            f"An error occurred while generating the reply: {e}",
            status_code=500
        )
