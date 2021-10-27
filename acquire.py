from requests import get
from bs4 import BeautifulSoup
import pandas as pd
import os, re


def get_all_blog_articles(target:str):
    '''Takes a target url and will compile a dataframe for each url
    '''
    base = re.match(r'^.*(?:com|org|gov|net|us|eu|tv|me|.co)', target)[0]
    # extract only the alphanum
    filename = re.sub(r'[^a-zA-Z0-9]', '', base)+'_blog_articles.csv'
    if os.path.exists(filename):
        return pd.read_csv(filename, index_col=[0])

    valid_urls = fetch_all_urls(target)
    blog_articles = list()
    for url in valid_urls.http:
        blog_articles.append(get_blog_article(str(url)))
    df = pd.DataFrame(blog_articles)
    df.to_csv(filename)
    return df

def get_blog_article(url):
        try:
            headers = {'User-Agent': 'Codeup Data Science'}
            response = get(url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            article = soup.find_all('p')
            content = list()
            for each in article:
                content.extend([r for r in re.findall(r'>(.*?)<', str(each)) if r != ''])
            content = ''.join(content)
            
            # Pulls phone numbers out of content
            phone_regex = r'''(?P<country_code>\+?1)?.?(?P<area_code>\d{3})?[\)].(?P<phone1>\d{3}).(?P<phone2>\d{4})'''
            verb_item_pat = re.compile(phone_regex, re.VERBOSE)
            # Joins the phone numbers into just digits
            phone_numbers = [''.join(num) for num in verb_item_pat.findall(content)]
            
            # Pulls the date out of content
            date_regex = r'(?P<month>:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s(\d{2})\,\s(\d{4})'
            date = [''.join(d) for d in re.findall(date_regex, content)]
            
            #Pulls author out of the content
            author_regex = r'By\s(?P<author_first_name>\w+)?\s(?P<author_lastname>\w+).'
            author = re.findall(author_regex, content, re.VERBOSE)
            
            #Pulls the copyright date from page
            copy_regex = r'''©\s(?P<copyright>.*?)?\s'''
            copyright = re.findall(copy_regex, content)

            try:
                title = soup.title.string
            except:
                title = None
            
            result = {
                'url': url,
                'title': title,
                'content': content,
                'phone_numbers': phone_numbers,
                'date': date,
                'author': author,
                'copyright': copyright
            }

        except Exception as e:
            print(e)
            print(f'{url} returned error')
            pass
        
        return result


def get_article_text(url):
    '''takes a url and checks if that file exists, file structure is 'article.txt'. If
    the file does not exist, then it will attempt to fetch the main content and create the file.
    '''
    
    # Extract the page from the url
    regex = r'com/(.*)/'
    filename = f'article_{re.findall(regex, url)[0]}.txt'
    
    # check if the file already exists 
    if os.path.exists(filename):
        with open(filename) as f:
            return f.read()
    
    # If the file doesn't exist, fetch the data and create the file
    headers = {'User-Agent': 'Codeup Data Science'}
    response = get(url, headers=headers)
    soup = BeautifulSoup(response.text)
    article = soup.find('div', id='main-content')
    txt = article.text
    
    # Save the article for next time
    with open(filename, 'w') as f:
        f.write(txt)
    
    return txt

def fetch_all_urls(target: str)->list:
    '''Pass a target url to crawl to get all valid urls from the target, will return a pandas 
    DataFrame must pass a valid URL as target
    '''
    
    def add_valid_urls(parse_url, valid_urls, invalid_urls, done, base):
        '''Builds out a list of valid_urls, invalid_urls and flags if is done.
        '''
        headers = {'User-Agent': 'Codeup Data Science'}

        # What url is being parsed
        print(f'Parsing {parse_url}')

        # Pull the base url out
        response = get(parse_url, headers=headers)
        soup = BeautifulSoup(response.text)

        # Fetches all anchors from page
        anchors = soup.find_all('a')

        # Pulls all hyperlinks from the anchors
        regex = r'''<a\s+(?:[^>]*?\s+)?href="(.*?)"'''
        # checks if the urls have http in them or not and concats with base if not to test
        unchecked_urls = [base+url if 'http' not in url else url for url in re.findall(regex, str(anchors))]

        urls = list()

        # Check through urls to see what ones are not already checked
        for url in unchecked_urls:
            # Make string to check
            url = str(url)
            # Checks if url is in valids or invalid urls, then ensure's that 'codeup'
            # is within the url and ensures that it isn't already in the checked urls list
            if url in valid_urls or url in invalid_urls \
                or 'codeup' not in url or url in urls:
                pass
            else:
                # Add to urls to test
                urls.append(url)

        # If there are not any more url's to check, make done flag true
        if len(urls) == 0:
            done = True
            return valid_urls, invalid_urls, done

        # Iterates through all the new urls and checks to see if they are valid
        for url in urls:
            url = str(url)
            try:
                print('Testing', url)
                # Test to see if response
                response = get(url, headers=headers)

                # Check response codes
                code = response.status_code

                # Enusre is valid and that url is not already added
                if code == 200:
                    valid_urls.append(url)

            except Exception as e:
                # Add to invalid_urls
                invalid_urls.append(url)

        return valid_urls, invalid_urls, False
    
    # Set the valid urls to target to start there
    valid_urls = [target]
    invalid_urls = []
    tried = list()
    done = False
    base = re.match(r'^.*(?:com|org|gov|net|us|eu|tv|me|.co)', valid_urls[0])[0]
    # extract only the alphanum
    filename = re.sub(r'[^a-zA-Z0-9]', '', base)+'_valid_urls.csv'
    if os.path.exists(filename):
        return pd.read_csv(filename, index_col=[0])
    while True:
        for url in valid_urls:
            if url not in tried:
                print(f'Trying {url}')
                tried.append(url)
                valid_urls, invalid_urls, done = add_valid_urls(url, valid_urls, invalid_urls, done, base)
            if done:
                break
        if done:
            break
    result = pd.DataFrame([{'http':url} for url in valid_urls])
    result.to_csv(filename)
    return result