FONT_SIZE = "1rem"
MARGIN_TOP_XL = "2.5vh"
MARGIN_TOP_SM = "1vh"

def generate_html_template(title, msg, font_size=FONT_SIZE, margin_top_xl=MARGIN_TOP_XL, margin_top_sm=MARGIN_TOP_SM):
    return f"""
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" />
    <link
        href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap"
        rel="stylesheet" />
    <link rel="stylesheet" href="https://pro.fontawesome.com/releases/v5.10.0/css/all.css" />
    <style>
        * {{
            font-family: "Ubuntu", sans-serif;
            list-style: none;
            text-decoration: none;
            outline: none !important;
            color: white;
            overflow-wrap: anywhere;
        }}
        body {{
            background-color: #0D1117;
        }}
        .container {{
            margin: 0vh 1vw;
            margin-bottom: 1vh;
            padding: 1vh 3vw;
            display: flex;
            flex-direction: column;
            border: 2px solid rgba(255, 255, 255, 0.11);
            border-radius: 20px;
            background-color: #161b22;
            align-items: center;
        }}
        .container.center {{
            text-align: center;
        }}
        .container.start {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }}
        .rfontsize {{
            font-size: {font_size};
        }}
        .withhover:hover {{
            filter: invert(0.3);
        }}
        .topmarginxl {{
            margin-top: {margin_top_xl};
            display: inline-block;
        }}
        .topmarginsm {{
            margin-top: {margin_top_sm};
            display: inline-block;
        }}
    </style>
</head>
<body>
{msg}
</body>
</html>
"""

html_content = generate_html_template(title=fileName, msg=msg)
