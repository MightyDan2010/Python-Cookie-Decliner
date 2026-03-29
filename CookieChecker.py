import re
import json
import time
import os
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

def save_to_json(filepath, global_stats, site_results): 
    data = {"global_statistics": global_stats, "site_results": site_results}
    temp_filepath = f"{filepath}.tmp"
    with open(temp_filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    os.replace(temp_filepath, filepath)

def visit_sites():
    global_stats = {"total_sites_audited": 0, "no_decline_button_found": 0, "total_cookies_mapped": 0, "total_first_party": 0, "total_third_party": 0, "list_of_third_party": []}
    audit_results = []
    output_file = "Results.json"
    button_clicked = 0
    try:
        with open('Information.json', 'r', encoding='utf-8') as f:
            domains = json.load(f)
    except FileNotFoundError:
        print("Information.json not found.")
        return

    print(f"--- Simulation Started ({len(domains)} sites) ---")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for domain in domains:
            url = domain if domain.startswith('http') else f"https://{domain}"
            parsed_url = urlparse(url)
            base_host = parsed_url.netloc.replace("www.", "")
            print(f"\n[{global_stats['total_sites_audited'] + 1}/{len(domains)}] Testing: {url}")
            context = browser.new_context(locale="en-US", user_agent="Mozilla/5.0...")
            page = context.new_page()
            site_data = {"domain": base_host,"pre_click_cookies": 0, "post_click_cookies": 0, "third_party_count": 0, "storage_items": 0, "button_found": False, "error": None, "all_third_party_cookie_names": []}

            try:
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(4000) 
                site_data["pre_click_cookies"] = len(context.cookies())
                decline_phrases = re.compile(r"reject all|decline|deny|reject|alle ablehnen", re.IGNORECASE)
                found_button = page.get_by_role("button", name=decline_phrases).first
                if found_button.is_visible():
                    found_button.click()
                    site_data["button_found"] = True
                    button_clicked = 1
                    page.wait_for_timeout(3000)
                else:
                    global_stats["no_decline_button_found"] += 1
                    button_clicked = 0
                    
                cookies_after = context.cookies()
                site_data["post_click_cookies"] = len(cookies_after)
                global_stats["total_cookies_mapped"] += len(cookies_after)

                for cookie in cookies_after:
                    c_domain = cookie['domain'].lstrip('.')
                    is_third_party = base_host not in c_domain and c_domain not in base_host
                    cookie_info = f"'{cookie['name']}' (Domain: {cookie['domain']}, Found on: {base_host})"
                    if is_third_party:
                        if button_clicked == 1:
                            global_stats["total_third_party"] += 1
                            global_stats["list_of_third_party"].append(cookie_info)
                            site_data["third_party_count"] += 1
                            site_data["all_third_party_cookie_names"].append(cookie['name'])
                        else:
                            site_data["third_party_count"] += 1
                            site_data["all_third_party_cookie_names"].append(cookie['name'])
                    else:
                        global_stats["total_first_party"] += 1
                        
            except Exception as e:
                site_data["error"] = str(e).split('\n')[0]
            finally:
                context.close()
                
            global_stats["total_sites_audited"] += 1
            audit_results.append(site_data)
            save_to_json(output_file, global_stats, audit_results)
            time.sleep(1)
    
        browser.close()

if __name__ == "__main__":
    visit_sites()
