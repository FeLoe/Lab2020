#!/usr/bin/env python3
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import WebDriverException 
import time
import dateparser
import re
from langdetect import detect
import json
import datetime
from sys import argv



def scrape_links(geckopath=None, filename="output.json"):
    #Set up Selenium
    if geckopath:
        browser = webdriver.Firefox(executable_path = geckopath)
    else:
        try:
            browser = webdriver.Firefox()
        except WebDriverException:
            print("Geckodriver not found. Either copy the geckodriver to your path or specify its location")
            return None
    #Get website, allow 15 seconds to scan the QR code
    browser.get("https://web.whatsapp.com/")
    time.sleep(15)
    #Get all the chats, sort them by date to know which one is first/last and save it into a list
    chats = []
    names = []
    n = 0
    maintext = browser.find_element_by_xpath('//h1').text
    language = detect(maintext)
    links_per_chat = []
    while True:
        #Get language
        #Get names of chats
        a = browser.find_elements_by_xpath("//div[@id='pane-side']//span[@title and @dir='auto']")
        new_chats = []
        for item in a:
            try: 
                #Get date of chat (two different options depending on whether it is a date/time)
                try: 
                    x = item.find_element_by_xpath('../following-sibling::div')
                except:
                    x = item.find_element_by_xpath('../../following-sibling::div')
            except:
                pass
            #Parse the date (is done automatically)
            try:
                parsed_date = dateparser.parse(x.text, settings={'DATE_ORDER': 'DMY'})
            except:
                parsed_date = ""
            #Put all the info (xpath element, name of chat, date) in one list
            try:    
                new_chats.append((item, item.text, parsed_date))
            except:
                pass
        #Sort by date, only keep the new chats
        new_chats.sort(key = lambda x: x[2], reverse = True)
        new_chats = [x for x in new_chats if x not in chats]
        new_chats.sort(key = lambda x: x[2], reverse = True)
        new_names = [x[1] for x in new_chats]

        #For every chat get all the links (including who sent them when)

        for c in new_chats: 
            links = []
            c[0].click()
            try: 
                x = browser.find_element_by_xpath("//div[@id = 'main']/header/div/div/img")
            except:
                x = browser.find_element_by_xpath("//div[@id = 'main']/header//*[@dir = 'auto']")
            x.click()
            time.sleep(2)
            if language == 'de':
                linktext = browser.find_element_by_xpath("//*[text() = 'Medien, Links und Dokumente']")
            elif language == 'nl':
                linktext = browser.find_element_by_xpath("//*[text() = 'Media, links en docs']")
            elif language == 'en':
                linktext = browser.find_element_by_xpath("//*[text() = 'Media, Links and Docs']")
            else: 
                print('language not supported')
                browser.quit()
            linktext.click()
            time.sleep(2)
            linktext2 = browser.find_element_by_xpath("//*[text() = 'Links']")
            linktext2.click()
            time.sleep(5)
            #Get all of the links, difference between inlinks (other people writing) and outlinks (own messages)
            while True: 
                inlinks = browser.find_elements_by_xpath("//*[@data-list-scroll-container = 'true']//*[contains(@class,'message-in')]//a")
                outlinks = browser.find_elements_by_xpath("//*[@data-list-scroll-container = 'true']//*[contains(@class,'message-out')]//a")
                #Scroll to get all the links
                if not inlinks:
                    newlinks_in = []
                else: 
                    last_link_in = inlinks[-1]
                    browser.execute_script("arguments[0].scrollIntoView();", last_link_in)
                    time.sleep(2)
                    newlinks_in = browser.find_elements_by_xpath("//*[@data-list-scroll-container = 'true']//*[contains(@class,'message-in')]//a")
                if not outlinks:
                    newlinks_out = []
                else:
                    last_link_out = outlinks[-1]
                    browser.execute_script("arguments[0].scrollIntoView();", last_link_out)
                    time.sleep(2)
                    newlinks_out = browser.find_elements_by_xpath("//*[@data-list-scroll-container = 'true']//*[contains(@class,'message-out')]//a")
                if (set(newlinks_in).issubset(inlinks)) and (set(newlinks_out).issubset(outlinks)):
                        break
            time.sleep(2)
            #Get message around link and sender (if from group)
            messages_in = []
            messages_out = []
            for link in inlinks: 
                link_final = link.get_attribute('href')
                text = link.find_elements_by_xpath('..')
                text = [t.text for t in text]
                sender = link.find_elements_by_xpath('../../../../preceding-sibling::div/span[@dir = "auto"]|../preceding-sibling::div/div/span[@dir = "auto"]')
                sender = [s.text for s in sender]
                message = {"link":link_final, "text":text, "sender":sender}
                messages_in.append(message)
            for link in outlinks:
                link_final = link.get_attribute('href')
                text = link.find_elements_by_xpath('..')
                text = [t.text for t in text]
                message = {"link":link_final, "text":text}
                messages_out.append(message)
            links_per_chat.append({'chatname':c[1], "date":c[2], "messages_in":messages_in, "messages_out":messages_out})

        #Scroll down to get the next group of chats
        if n == 0:
            chats = new_chats
            names = new_names
            for i in range(-1, (-len(new_chats)-1), -1):
                try:
                    browser.execute_script("arguments[0].scrollIntoView();", new_chats[i][0])
                    time.sleep(2)
                    break
                except:
                    pass
        else:
            if set(new_names).issubset(names):
                break
            else:
                chats.extend(x for x in new_chats if x not in chats)
                chats.sort(key = lambda x: x[2], reverse = True)
                names = [x[1] for x in chats]
                for i in range(-1, (-len(new_chats)-1), -1):
                    try:
                        browser.execute_script("arguments[0].scrollIntoView();", new_chats[i][0])
                        time.sleep(2)
                        break
                    except:
                        pass
        n += 1
        if n == 1:
            break
    browser.quit()
    def myconverter(o):
        if isinstance(o, datetime.datetime):
            return o.__str__()
    with open(filename, 'w') as fout:
        json.dump(links_per_chat , fout, default = myconverter)
    return links_per_chat

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--geckopath", help="Path to your gecko driver (necessary if not in $PATH)")
    parser.add_argument("--output", help="File to store the output")
    args = parser.parse_args()

    scrape_links(geckopath = args.geckopath)

#def anonymize_data(whatsapp_data):
    #Todo: Hash all the names of the chats/senders
    #Todo: For all links from the other person: whitelist
    #Todo: For all text from the other person: only get common words?
    #Todo: Remove all identifiers from the URLs


