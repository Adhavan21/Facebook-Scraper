from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import time
import streamlit as st
import pandas as pd

website = 'https://www.facebook.com/login'

def show_feed(scraped) :
    for i in scraped :
        with st.container(border=True) :
            st.write(i['caption'])
            for j in i['images'] :
                st.markdown(f"![Alt Text]({j})")
            st.write(f'{i['reactions']} reactions      {i['comments']} comments      {i['shares']} shares')

def scrape(url,email,password,by='Post Count',until=10) :
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")  # Disable notifications
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2
    })
    driver = webdriver.Chrome(options=chrome_options)

    driver.get(website)
    with st.spinner("Logging in....") :
        email_field = driver.find_element(By.XPATH,'//input[@id="email"]')
        email_field.click()
        time.sleep(1)
        for i in email :
            time.sleep(0.2) #0.2 second delay between entering each character
            email_field.send_keys(i)

        time.sleep(0.8)

        password_field = driver.find_element(By.XPATH,'//input[@id="pass"]')
        password_field.click()
        time.sleep(0.9)
        for i in password :
            time.sleep(0.15)
            password_field.send_keys(i)

        login_button = driver.find_element(By.XPATH,'//button[@name="login"]')
        login_button.click()

    with st.spinner("Waiting for the page to load....") :
        search_button = driver.find_element(By.XPATH,'//input[@aria-label="Search Facebook"]') #waiting for the home page
        wait = WebDriverWait(driver, timeout=2)
        wait.until(lambda d : search_button.is_displayed())
        time.sleep(2)

        driver.get(url)

        c = 0
        posts = []
        captions = []
        flag = True

    with st.spinner('Scrolling...') :
        if by != 'Scroll Until...' :
            scroll_bar = st.progress(0) 
        while flag :
            time.sleep(1)
            div_xpath = '''
            //div[@class="html-div xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd"]
                [count(div) = 2]
                [div[1][@dir="auto"]]
                [div[2][@id]]
            '''
            div_elements = driver.find_elements(By.XPATH, div_xpath)

            try :
                see_more = driver.find_elements(By.XPATH,'//div[text()="See more"]')
                for index, div in enumerate(see_more) :
                    driver.execute_script("arguments[0].click();", div)  #clicks 'see more' to extract full caption
                    print('\nClicked See more')
            except NoSuchElementException :
                print("No See More Button")
        
            for index, div in enumerate(div_elements):
                try:
                    # Extract text content of the first child div (Caption div)
                    first_child = div.find_element(By.XPATH, "./div[1]")
                    text_content = first_child.text.strip() if first_child.text else ""

                    # Extract all img src inside the second child div (Image div)
                    second_child = div.find_element(By.XPATH, "./div[2]")
                    img_elements = second_child.find_elements(By.XPATH, ".//img[@src]")  # Find all images

                    # Get src of all img elements
                    img_srcs = [img.get_attribute("src") for img in img_elements]
                    img_alt = [img.get_attribute("alt") for img in img_elements]

                    try:
                        span_element = div.find_element(By.XPATH, './following-sibling::div[1]//div[text()="All reactions:"]/following::span[1]')
                        reactions = span_element.text.strip() if span_element.text else ""
                        
                    except NoSuchElementException:
                        reactions = "0"

                    try:
                        comment_element = div.find_element(By.XPATH, ".//following::span[contains(text(), 'comment')]")
                        comments = comment_element.text.strip() if comment_element.text else ""
                        comments = comments.split(' ')[0]
                                            
                    except NoSuchElementException:
                        comments = "0"

                    try:                    
                        share_element = div.find_element(By.XPATH, ".//following::span[contains(text(), 'share')]")
                        shares = share_element.text.strip() if share_element.text else ""    
                        shares = shares.split(' ')[0]                    
                        
                    except NoSuchElementException:
                        shares = "0"

                    if text_content not in captions :
                        if by=='Scroll Until...' and until in text_content : #break loop if the 'until' post is reached
                            flag = False
                            break

                        captions.append(text_content)
                        posts.append({
                            "caption": text_content,
                            "images": img_srcs,
                            "image_alt" : img_alt,
                            "reactions" : reactions,
                            'comments' : comments,
                            'shares' : shares
                        })

                        posts[-1]['images'] = []
                        posts[-1]['emojis'] = []
                        for i in img_srcs : #separating images and emojis
                            if 'scontent' in i :
                                posts[-1]['images'].append(i)
                            else :
                                posts[-1]['emojis'].append(i)

                    if by == 'Post Count' and len(posts) >= until : #break loop if required number of posts has been scraped
                        flag = False
                        break

                except Exception as e:
                    print(f"Error processing div {index}: {e}")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);") #scroll
            c = c+1
            print('\nScrolled',c,'times')

            #Loop Break conditions
            if by=='Post Count' :
                scroll_bar.progress(round(len(posts)*(100/until)), text=f'Scaped {len(posts)} posts')
            elif by=='Scroll Count' :
                scroll_bar.progress(round(c*(100/until)), text=f'Scrolled {c} times')
            if by == 'Post Count' and len(posts) >= until :
                posts = posts[:until]
                flag = False
            elif by == 'Scroll Count' and c >= until :
                flag = False

        time.sleep(2)
        if by != 'Scroll Until...' :
            scroll_bar.empty()
        return posts
        

#Streamlit UI
#st.header('Facebook Scraper')
st.title('Facebook Scraper')
if 'data' not in st.session_state :
    st.session_state['data'] = None

by = st.radio('Scrape By : ',['Post Count', 'Scroll Count', 'Scroll Until...'],horizontal=True)

with st.form(key='scraper') :
    url = st.text_input('Enter the page URL :')
    email = st.text_input('Enter the Email id :')
    password = st.text_input('Enter the password :',type='password')
    if by == 'Scroll Count' :
        until = st.slider('Scroll count : ',1,50,10)
    if by == 'Post Count' :
        until = st.slider('Posts count : ',1,50,10)
    if by == 'Scroll Until...' :
        until = st.text_input('Scroll Until...')
    
    submit = st.form_submit_button('Scrape')

if submit :
    st.session_state.data = scrape(url,email,password,by,until)

if st.session_state.data != None :
    st.write(f'{len(st.session_state.data)} posts scraped.')
    with st.expander("Feed") :
        st.session_state.feed = True
        show_feed(st.session_state.data)

    format = st.segmented_control('Data Format :',['JSON','Table'],default='JSON')
    with st.expander("Data") :
        if format == 'JSON' :
            st.write(st.session_state.data)
        else :
            st.write(pd.DataFrame(st.session_state.data))

                

