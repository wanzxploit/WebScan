from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.panel import Panel
from rich.style import Style
import requests
import socket
import ssl
import whois
import dns.resolver
from datetime import datetime
import urllib.parse
import time
import concurrent.futures
import os
import platform
import pyfiglet

COLORS = {
    'primary': 'deep_sky_blue2',
    'secondary': 'slate_blue3',
    'success': 'green3',
    'warning': 'yellow3',
    'error': 'red3',
    'info': 'cyan2',
    'text': 'grey84',
    'highlight': 'grey84'
}

console = Console()

def clean_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def clean_url(url):
    url = url.strip().lower()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def get_domain(url):
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc

def format_date(date_str):
    if not date_str:
        return "Not Available"
    try:
        if isinstance(date_str, str):
            date_obj = datetime.strptime(date_str, "%b %d %H:%M:%S %Y GMT")
        else:
            date_obj = date_str
        return date_obj.strftime("%d %B %Y")
    except Exception:
        return str(date_str)

def get_security_headers(headers):
    security_headers = {
        'Strict-Transport-Security': 'HSTS',
        'Content-Security-Policy': 'CSP',
        'X-Frame-Options': 'X-Frame',
        'X-Content-Type-Options': 'X-Content-Type',
        'X-XSS-Protection': 'XSS Protection',
        'Referrer-Policy': 'Referrer Policy',
        'Feature-Policy': 'Feature Policy'
    }
    return {new_name: headers.get(header, 'Not Available') 
            for header, new_name in security_headers.items()}

def check_admin_panel(url, timeout=3):
    admin_paths = ['/admin', '/administrator', '/wp-admin', '/login', 
                  '/panel', '/admin.php', '/admin/login', '/cp']
    found_paths = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        def check_path(path):
            try:
                test_url = url.rstrip('/') + path
                response = requests.get(test_url, timeout=timeout, allow_redirects=False)
                if response.status_code in [200, 301, 302, 403]:
                    return test_url
            except:
                pass
            return None
        
        futures = [executor.submit(check_path, path) for path in admin_paths]
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                found_paths.append(future.result())
    
    return found_paths

def grab_banner(url, timeout=5):
    try:
        response = requests.get(url, timeout=timeout)
        server = response.headers.get('Server', 'Not Available')
        x_powered_by = response.headers.get('X-Powered-By', 'Not Available')
        return server, x_powered_by
    except Exception as e:
        return f'Error: {str(e)}', 'Not Available'

def get_technologies(url):
    try:
        response = requests.get(url)
        return "Analysis not implemented"
    except:
        return "Not Available"

def get_server_location(url):
    try:
        response = requests.get(url)
        server_ip = response.raw._connection.sock.getpeername()[0]
        location = requests.get(f"https://ipinfo.io/{server_ip}/json").json()
        return location.get("city", "Not Available"), location.get("country", "Not Available")
    except:
        return "Not Available", "Not Available"

def create_styled_table(title):
    table = Table(
        title=title,
        title_style=Style(color=COLORS['primary'], bold=True),
        border_style=Style(color=COLORS['secondary']),
        header_style=Style(color=COLORS['highlight'], bold=True),
        pad_edge=False,
        expand=True
    )
    table.add_column("Category", style=Style(color=COLORS['info']), no_wrap=True)
    table.add_column("Details", style=Style(color=COLORS['text']))
    return table

def scan_website(url):
    try:
        url = clean_url(url)
        domain = get_domain(url)
        
        with Progress(
            SpinnerColumn(style=COLORS['primary']),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style=COLORS['success'], finished_style=COLORS['success']),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            main_table = create_styled_table(f"Website Scan Results: {url}")
            scan_task = progress.add_task(
                f"[{COLORS['info']}]Scanning...",
                total=100
            )
            
            progress.update(scan_task, advance=10, 
                          description=f"[{COLORS['info']}]Checking IP and DNS...")
            try:
                ip = socket.gethostbyname(domain)
                main_table.add_row("IP Address", ip)

                dns_records = dns.resolver.resolve(domain, 'A')
                dns_ips = [str(record) for record in dns_records]
                if dns_ips:
                    main_table.add_row("DNS Records", "\n".join(dns_ips))
            except Exception as e:
                main_table.add_row("Network Info", f"Error: {str(e)}")

            progress.update(scan_task, advance=20, 
                          description=f"[{COLORS['info']}]Checking SSL...")
            try:
                context = ssl.create_default_context()
                with socket.create_connection((domain, 443)) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        main_table.add_row("SSL Valid From", format_date(cert['notBefore']))
                        main_table.add_row("SSL Valid Until", format_date(cert['notAfter']))
            except Exception as e:
                main_table.add_row("SSL Status", f"Error: {str(e)}")

            progress.update(scan_task, advance=20, 
                          description=f"[{COLORS['info']}]Checking HTTP Headers...")
            try:
                response = requests.get(url, timeout=5)
                status_color = COLORS['success'] if response.status_code == 200 else COLORS['warning']
                main_table.add_row(
                    "HTTP Status",
                    f"[{status_color}]{response.status_code} ({response.reason})[/{status_color}]"
                )

                security_headers = get_security_headers(response.headers)
                for header, value in security_headers.items():
                    main_table.add_row(header, value)
            except Exception as e:
                main_table.add_row("HTTP Status", f"Error: {str(e)}")

            progress.update(scan_task, advance=20, 
                          description=f"[{COLORS['info']}]Fetching WHOIS Info...")
            try:
                domain_info = whois.whois(domain)
                if domain_info.creation_date:
                    creation_date = domain_info.creation_date[0] if isinstance(domain_info.creation_date, list) else domain_info.creation_date
                    main_table.add_row("Domain Created", format_date(creation_date))
                if domain_info.expiration_date:
                    expiration_date = domain_info.expiration_date[0] if isinstance(domain_info.expiration_date, list) else domain_info.expiration_date
                    main_table.add_row("Domain Expiry", format_date(expiration_date))
            except Exception as e:
                main_table.add_row("WHOIS Info", f"Error: {str(e)}")

            progress.update(scan_task, advance=10, 
                          description=f"[{COLORS['info']}]Checking Admin Panel...")
            admin_panels = check_admin_panel(url)
            if admin_panels:
                main_table.add_row("Admin Panel", "\n".join(admin_panels))
            else:
                main_table.add_row("Admin Panel", "Not Found")

            progress.update(scan_task, advance=10, 
                          description=f"[{COLORS['info']}]Fetching Server Info...")
            server, x_powered_by = grab_banner(url)
            main_table.add_row("Server", server)
            main_table.add_row("X-Powered-By", x_powered_by)

            progress.update(scan_task, advance=10, 
                          description=f"[{COLORS['info']}]Detecting Technologies...")
            technologies = get_technologies(url)
            main_table.add_row("Technologies", technologies)

            progress.update(scan_task, advance=10, 
                          description=f"[{COLORS['info']}]Locating Server...")
            city, country = get_server_location(url)
            main_table.add_row("Server Location", f"{city}, {country}")

            progress.update(scan_task, completed=100, 
                          description=f"[{COLORS['success']}]Scan Complete!")
            time.sleep(0.5)

        console.print(main_table)

    except Exception as e:
        console.print(Panel(f"Scan Error: {str(e)}", 
                          style=Style(color=COLORS['error'])))

if __name__ == "__main__":
    clean_screen()
    
    banner = pyfiglet.figlet_format(" WebScan", font="slant")
    console.print(Panel(
        f"[{COLORS['primary']}]{banner}[/{COLORS['primary']}]",
        subtitle="Web Scanner By Wanz Xploit",
        border_style=Style(color=COLORS['secondary'])
    ))

    try:
        url_input = console.input(f"[{COLORS['primary']}] Enter website URL: [/{COLORS['primary']}]").strip()
        if not url_input:
            console.print(Panel("URL cannot be empty!", 
                              style=Style(color=COLORS['error'])))
        else:
            scan_website(url_input)
    except KeyboardInterrupt:
        console.print(Panel("\nScan canceled by user.", 
                          style=Style(color=COLORS['warning'])))
    except Exception as e:
        console.print(Panel(f"Error: {str(e)}", 
                          style=Style(color=COLORS['error'])))