import json
import os
import time
import traceback
from threading import Semaphore, Thread, Lock

import requests
from bs4 import BeautifulSoup
from mss import mss
from googletrans import Translator
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from selenium.webdriver.firefox.service import Service
from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager

thread_count = 10
semaphore = Semaphore(thread_count)
lock = Lock()

translator = Translator()


def uploadToGoogleDrive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    path = f"{os.getcwd()}/screenshots"
    f = None
    for x in os.listdir(path):
        try:
            print("Uploading", x)
            f = drive.CreateFile({'title': x})
            f.SetContentFile(os.path.join(path, x))
            f.Upload()
            # Due to a known bug in pydrive if we don't empty the variable used to  upload the files to Google Drive the
            # file stays open in memory and causes a memory leak, therefore preventing its deletion
            f = None
            if f:
                pass
            print(f"Uploaded {x}")
            os.remove(os.path.join(path, x))
        except:
            traceback.print_exc()
            print(f"Unable to upload {x}")


uploadToGoogleDrive()


def getData(addr):
    file = f'./reports/{addr}.json'
    if os.path.exists(file):
        print(f'File {file} already exists')
        return
    with semaphore:
        url = f"https://www.bitcoinabuse.com/reports/{addr}"
        print(url)
        with lock:
            driver.get(url)
            while "server error" in driver.page_source.lower():
                print("Server error, retrying")
                driver.get(url)
                time.sleep(1)
            try:
                driver.maximize_window()
            except:
                pass
            time.sleep(1)
            takeScreenshot(f'./screenshots/{addr}.png')
            soup = BeautifulSoup(driver.page_source, 'lxml')
        data = {}
        page_count = soup.find_all('a', {'class': 'page-link'})
        if page_count:
            print(f"Page count ({addr}): ", page_count[-2].text)
        for tr in soup.find('table', {"id": 'summary-table'}).find_all('tr'):
            data[tr.find('th').text] = tr.find('td').text
        data['Address'] = addr
        reports = soup.find('table', {'class': 'table table-striped table-bordered table-responsive-lg'})
        ths = reports.find().find_all('th')
        data['reports'] = []
        next_page = True
        while next_page:
            for tr in reports.find_all('tr'):
                tds = tr.find_all('td')
                try:
                    # report = {ths[i].text: translator.translate(tds[i].text).text for i in range(len(tds))}
                    # json.dumps(report, indent=4)
                    report = {ths[i].text: tds[i].text for i in range(len(tds))}
                except:
                    print("Unable to translate")
                    traceback.print_exc()
                    report = {ths[i].text: tds[i].text for i in range(len(tds))}
                if report != {}:
                    data['reports'].append(report)
            next_page = soup.find('a', {'rel': 'next'})
            if next_page:
                soup = getSoup(next_page['href'])
                print(next_page['href'])
                reports = soup.find('table', {'class': 'table table-striped table-bordered table-responsive-lg'})
        print(json.dumps(data, indent=4))
        with open(file, 'w') as f:
            json.dump(data, f, indent=4)
        return data


def takeScreenshot(file_name):
    driver.execute_script("window.scrollBy(0,370)", "")
    # driver.save_full_page_screenshot(file_name)
    mss().shot(mon=-1, output=file_name)


def processPages():
    report = {}
    next_page = 'https://www.bitcoinabuse.com/reports'
    threads = []
    while next_page:
        try:
            print(next_page)
            soup = getSoup(next_page)
            for div in soup.find_all('div', {'class': 'col-xl-4 col-md-6 mb-3'}):
                addr = div.find('a').text
                threads.append(Thread(target=getData, args=(addr,)))
                threads[-1].start()
                if addr not in report:
                    report[addr] = 0
                report[addr] += 1
            # print("Breaking on first page!!")
            # break
            next_page = soup.find('a', {'rel': 'next'})
            if next_page:
                next_page = next_page['href']
        except:
            traceback.print_exc()
    with open('report.json', 'w') as f:
        json.dump(report, f, indent=4)
    print("All pages done!! Now Waiting for threads to finish!!")
    for t in threads:
        t.join()
    print("All done!!")


def main():
    # getData('17g8bzF6fvGzWf2sWqbSx3vt66fbj7NTFm')
    processPages()


def initialize():
    logo()
    for d in ['screenshots', 'reports']:
        if not os.path.isdir(d):
            os.mkdir(d)


def getSoup(url):
    soup = BeautifulSoup(requests.get(url).content, 'lxml')
    while "server error" in soup.text.lower():
        print("Server error, retrying")
        soup = BeautifulSoup(requests.get(url).content, 'lxml')
        time.sleep(1)
    return soup


def logo():
    print(r"""
      ____   _  _               _                   _                       
     |  _ \ (_)| |             (_)           /\    | |                      
     | |_) | _ | |_  ___  ___   _  _ __     /  \   | |__   _   _  ___   ___ 
     |  _ < | || __|/ __|/ _ \ | || '_ \   / /\ \  | '_ \ | | | |/ __| / _ \
     | |_) || || |_| (__| (_) || || | | | / ____ \ | |_) || |_| |\__ \|  __/
     |____/ |_| \__|\___|\___/ |_||_| |_|/_/    \_\|_.__/  \__,_||___/ \___|
==================================================================================
             bitcoinabuse.com report downloader by @evilgenius786
==================================================================================
[+] CSV/JSON report output
[+] Takes screenshots of reports
[+] Translates reports to any language
__________________________________________________________________________________
""")


if __name__ == '__main__':
    try:
        initialize()
        print("Launching Firefox browser...")
        driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()))
        main()
    except:
        traceback.print_exc()
        input("Error occurred in execution, waiting for user input...")
