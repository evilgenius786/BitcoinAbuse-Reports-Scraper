import json
import os
import time
from threading import Semaphore, Thread

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.firefox.service import Service
from translate import Translator
from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager

thread_count = 10
semaphore = Semaphore(thread_count)


def getData(addr):
    file = f'./reports/{addr}.json'
    if os.path.exists(file):
        print(f'File {file} already exists')
        return
    with semaphore:
        url = f"https://www.bitcoinabuse.com/reports/{addr}"
        print(url)
        driver.get(url)
        try:
            driver.maximize_window()
        except:
            pass
        time.sleep(1)
        driver.save_full_page_screenshot(f'./screenshots/{addr}.png')
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


def processPages():
    next_page = 'https://www.bitcoinabuse.com/reports'
    threads = []
    while next_page:
        print(next_page)
        soup = getSoup(next_page)
        for addr in soup.find_all('div', {'class': 'col-xl-4 col-md-6 mb-3'}):
            threads.append(Thread(target=getData, args=(addr.find('a').text,)))
            threads[-1].start()
        next_page = soup.find('a', {'rel': 'next'})
        if next_page:
            next_page = next_page['href']
    print("All pages done!! Now Waiting for threads to finish!!")
    for t in threads:
        t.join()
    print("All done!!")


def main():
    initialize()
    # getData('17g8bzF6fvGzWf2sWqbSx3vt66fbj7NTFm')
    processPages()


def initialize():
    logo()
    for d in ['screenshots', 'reports']:
        if not os.path.isdir(d):
            os.mkdir(d)


def getSoup(url):
    return BeautifulSoup(requests.get(url).content, 'lxml')


def translate():
    translator = Translator(to_lang="German")
    translation = translator.translate("Good Morning!")
    print(translation)


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
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()))
    main()
