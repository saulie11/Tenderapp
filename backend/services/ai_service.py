import os
import json
import anthropic

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def analyze_tender_document(text_content: str) -> dict:
    """Extract structured data from a tender document."""
    client = get_client()
    prompt = f"""Analyze the following tender document and extract key information.
Return a JSON object with these fields (use null if not found):
- title: tender title
- reference_number: reference or tender number
- issuing_body: organization issuing the tender
- description: brief description (2-3 sentences)
- category: category/sector (e.g. IT, Construction, Consulting)
- value: estimated contract value
- currency: currency code
- closing_date: closing date in ISO format (YYYY-MM-DDTHH:MM:SS) or null
- published_date: publication date in ISO format or null
- key_requirements: list of top 5 key requirements
- evaluation_criteria: list of evaluation criteria
- eligibility_criteria: eligibility requirements

Document:
{text_content[:8000]}

Respond with ONLY the JSON object, no other text."""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError):
        return {"description": message.content[0].text}


def generate_tender_summary(tender_data: dict) -> str:
    """Generate a concise summary of a tender."""
    client = get_client()
    prompt = f"""Write a concise 3-4 sentence summary of this tender opportunity for a business deciding whether to bid:

Title: {tender_data.get('title', 'N/A')}
Issuing Body: {tender_data.get('issuing_body', 'N/A')}
Description: {tender_data.get('description', 'N/A')}
Value: {tender_data.get('value', 'N/A')}
Closing Date: {tender_data.get('closing_date', 'N/A')}

Focus on: what is required, who it's for, key value/opportunity, and urgency."""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def write_tender_document(instruction: str, tender_context: dict = None, document_type: str = "proposal") -> str:
    """AI-assisted document writing for tender submissions."""
    client = get_client()

    context_str = ""
    if tender_context:
        context_str = f"""
Tender Details:
- Title: {tender_context.get('title', 'N/A')}
- Issuing Body: {tender_context.get('issuing_body', 'N/A')}
- Description: {tender_context.get('description', 'N/A')}
- Value: {tender_context.get('value', 'N/A')}
- Closing Date: {tender_context.get('closing_date', 'N/A')}
- Requirements: {tender_context.get('notes', 'N/A')}
"""

    document_templates = {
        "proposal": "a comprehensive bid proposal",
        "cover_letter": "a professional cover letter for a tender submission",
        "executive_summary": "an executive summary for a tender bid",
        "methodology": "a technical methodology section",
        "company_profile": "a company profile/capability statement",
        "financial_proposal": "a financial proposal breakdown",
        "compliance_statement": "a compliance and eligibility statement",
    }

    doc_description = document_templates.get(document_type, "a professional tender document")

    prompt = f"""You are an expert tender writer. Write {doc_description}.

{context_str}

Instructions from user:
{instruction}

Write a professional, well-structured document. Use clear headings, bullet points where appropriate, and professional business language. Be specific and compelling."""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def improve_document(existing_content: str, improvement_instruction: str) -> str:
    """Improve or edit an existing document."""
    client = get_client()

    prompt = f"""You are an expert tender writer and editor. Improve the following document based on the instructions.

Current document:
{existing_content}

Improvement instructions:
{improvement_instruction}

Return the improved document. Maintain the same general structure unless instructed otherwise."""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def chat_with_ai(messages: list, tender_context: dict = None) -> str:
    """General AI chat for tender assistance."""
    client = get_client()

    system_prompt = """You are TenderAI, an expert assistant specializing in tender management, bid writing, and procurement.
You help businesses:
1. Understand tender requirements and evaluate opportunities
2. Write compelling bid documents and proposals
3. Track and manage tender submissions
4. Analyze tender documents and extract key information
5. Provide strategic advice on bidding

Be professional, specific, and practical. When writing documents, format them properly with headers and structure."""

    if tender_context:
        system_prompt += f"""

Current tender context:
- Title: {tender_context.get('title', 'N/A')}
- Issuing Body: {tender_context.get('issuing_body', 'N/A')}
- Description: {tender_context.get('description', 'N/A')}
- Status: {tender_context.get('status', 'N/A')}
- Closing Date: {tender_context.get('closing_date', 'N/A')}"""

    api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=3000,
        system=system_prompt,
        messages=api_messages,
    )
    return response.content[0].text


def check_tender_relevance(tender_text: str, keywords: list) -> dict:
    """Check if a tender matches keywords and assess relevance."""
    client = get_client()

    keywords_str = ", ".join(keywords) if keywords else "general business services"

    prompt = f"""Assess whether this tender opportunity is relevant for a company interested in: {keywords_str}

Tender:
{tender_text[:3000]}

Return a JSON object with:
- relevant: true/false
- relevance_score: 0-100
- reason: brief explanation (1-2 sentences)
- matched_keywords: list of matched keywords

Respond with ONLY the JSON object."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text)
    except (json.JSONDecodeError, IndexError):
        return {"relevant": True, "relevance_score": 50, "reason": "Could not assess automatically"}
