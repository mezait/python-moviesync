from urllib.parse import quote

def parse_html_params(args):
    arglist = []
    
    for key in sorted(args, key=lambda x: x.lower()):
        arglist.append(f"{key}={quote(str(args[key]), safe='')}")

    params = '&'.join(arglist)
    
    if len(params) > 0:
        params = f"&{params}"

    return params
