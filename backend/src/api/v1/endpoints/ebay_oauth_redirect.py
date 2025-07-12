"""
eBay OAuth Redirect Handler

This module provides a simple redirect handler for eBay OAuth flow
that captures the authorization code and displays it to the user.
"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/oauth/redirect/ebay", response_class=HTMLResponse)
async def ebay_oauth_redirect(
    request: Request,
    code: str = Query(None, description="Authorization code from eBay"),
    state: str = Query(None, description="State parameter for CSRF protection"),
    error: str = Query(None, description="Error from eBay OAuth"),
    error_description: str = Query(None, description="Error description"),
):
    """Handle eBay OAuth redirect and display the authorization code."""

    if error:
        return f"""
        <html>
            <head>
                <title>eBay Authorization Failed</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .error {{ color: #d32f2f; background: #ffebee; padding: 20px; border-radius: 4px; }}
                    .code {{ font-family: monospace; background: #f5f5f5; padding: 4px 8px; }}
                </style>
            </head>
            <body>
                <h1>eBay Authorization Failed</h1>
                <div class="error">
                    <p><strong>Error:</strong> <span class="code">{error}</span></p>
                    <p><strong>Description:</strong> {error_description or "No description provided"}</p>
                </div>
                <p>Please close this window and try again.</p>
            </body>
        </html>
        """

    if not code:
        return """
        <html>
            <head>
                <title>eBay Authorization Error</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .error { color: #d32f2f; }
                </style>
            </head>
            <body>
                <h1>eBay Authorization Error</h1>
                <p class="error">No authorization code received from eBay.</p>
                <p>Please close this window and try again.</p>
            </body>
        </html>
        """

    return f"""
    <html>
        <head>
            <title>eBay Authorization Successful</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .success {{ color: #2e7d32; background: #e8f5e9; padding: 20px; border-radius: 4px; }}
                .code-box {{
                    background: #f5f5f5;
                    border: 2px dashed #ccc;
                    padding: 20px;
                    margin: 20px 0;
                    font-family: monospace;
                    font-size: 14px;
                    word-break: break-all;
                }}
                .state-box {{
                    background: #fff3e0;
                    border: 1px solid #ffb74d;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                button {{
                    background: #1976d2;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                }}
                button:hover {{ background: #1565c0; }}
                .instructions {{
                    background: #e3f2fd;
                    padding: 15px;
                    border-radius: 4px;
                    margin-top: 20px;
                }}
            </style>
            <script>
                function copyCode() {{
                    const codeElement = document.getElementById('authCode');
                    const codeText = codeElement.textContent;
                    navigator.clipboard.writeText(codeText).then(() => {{
                        const button = document.getElementById('copyButton');
                        button.textContent = 'Copied!';
                        setTimeout(() => {{ button.textContent = 'Copy Code'; }}, 2000);
                    }});
                }}

                function copyState() {{
                    const stateElement = document.getElementById('stateValue');
                    const stateText = stateElement.textContent;
                    navigator.clipboard.writeText(stateText).then(() => {{
                        const button = document.getElementById('copyStateButton');
                        button.textContent = 'Copied!';
                        setTimeout(() => {{ button.textContent = 'Copy State'; }}, 2000);
                    }});
                }}
            </script>
        </head>
        <body>
            <h1>eBay Authorization Successful!</h1>
            <div class="success">
                <p>✅ You have successfully authorized VinylDigger to access your eBay account.</p>
            </div>

            <h2>Authorization Code:</h2>
            <div class="code-box" id="authCode">{code}</div>
            <button id="copyButton" onclick="copyCode()">Copy Code</button>

            <div class="state-box">
                <h3>State Value (for verification):</h3>
                <div class="code-box" id="stateValue">{state}</div>
                <button id="copyStateButton" onclick="copyState()">Copy State</button>
            </div>

            <div class="instructions">
                <h3>Next Steps:</h3>
                <ol>
                    <li>Copy the authorization code above</li>
                    <li>Go back to VinylDigger</li>
                    <li>Paste the code in the verification form</li>
                    <li>Also copy and paste the state value for security verification</li>
                </ol>
                <p><strong>Note:</strong> This code expires in a few minutes, so complete the process quickly.</p>
            </div>

            <p style="margin-top: 30px; color: #666;">You can close this window after copying the code.</p>
        </body>
    </html>
    """
