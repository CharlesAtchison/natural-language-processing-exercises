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

def fetch_all_urls(target: str, reparse=False)->list:

    '''
    '''
    # list of the invalid_urls
    invalid_urls = []
    # Base web url from target
    base = re.match(r'^.*(?:com|org|gov|net|us|eu|tv|me|.co)', target)[0]
    # extract only the base site from target
    site = re.findall(r'^https?://?(.*?)\.', base)[0]
    filename = site+'_profile.csv'
    # Default dict
    ### MODIFY THIS IN CONJUNCTION WITH THE PARSE_TARGET_DATA IF YOU ARE LOOKING FOR DIFFERENT ASPECTS OF A SITE###
    def_dict = {'title': 'None', 'content': 'None', 'phone_numbers': 'None', 
                'date': 'None', 'author': 'None', 'copyright': 'None', 'parsed': False}
    
    # Check if there is a file for that site
    if os.path.exists(filename):
        # Pull the dataframe in
        df = pd.read_csv(filename, index_col='url')
        # check if the target is in the dataframe
        if reparse:
            df.loc[target, 'parsed'] = False
            
        if target not in df.index.to_list():
            # Add target to the dataframe
            df.loc[target] = def_dict
            
    else:
        # If the dataframe does not exist, set the first value to the target
        # Set the url to the target
        def_dict['url'] = target
        df = pd.DataFrame([def_dict]).set_index('url')
            
    # Ensures there are no more urls to parse
    while df[~df.parsed].parsed.to_list() != []:
        # Pull the dataframe in again to ensure it's fresh each iteration
        if os.path.exists(filename):
        # Pull the dataframe in if it's not the first time
            df = pd.read_csv(filename, index_col='url')
            
        # Set the url to parse as the first element in the list
        url = df[~df.parsed].index[0]

        # Returns either None or a tuple containing the (url_dict, new_urls)
        valid = parse_target_data(url, base)
        
        if valid[0] is None:
            # Add invalid url to invalid urls
            df.drop(url, inplace=True)
            invalid_urls.append(url)
            df.to_csv(filename)
        else:
            # Pull out url_dict from the valid url and create temp_df to merge later
            
            # Drop the url portion of the def_dict
            try:
                def_dict.pop('url')
            except:
                pass
        
            urls = [str(u) for u in valid[1] if (u not in invalid_urls) & (site in str(u))]
            
            # Iterate though the new urls but check that they are not invalid first
            for n, eu in enumerate(urls):
            # Add each url to the index of the data frame and set the parse to False
                if eu not in df.index.to_list():
                    df.loc[eu] = def_dict
                
            # Mark the url as parsed
            new_vals = [v for v in valid[0].values()]
            
            df.loc[url] = new_vals
    
            # Save the dataframe so that it can continue to go through and check each url
        df.to_csv(filename)
        print(f'Parsed {url}')
            
    return df

def parse_target_data(url, base, headers={'User-Agent': 'Codeup Data Science'}):
    '''returns a dict of content and a list of url anchors from the target and 
    '''
    try:
        response = get(url, headers=headers)
        if response.status_code != 200:
            raise Exception
        soup = BeautifulSoup(response.text, 'html.parser')

        # Fetches all anchors from page
        anchors = soup.find_all('a')

        # Pulls all hyperlinks from the anchors
        regex = r'''<a\s+(?:[^>]*?\s+)?href="(.*?)"'''
        
        # checks if the urls have http in them or not and concats with base if not to test
        urls = [u for u in set(re.findall(regex, str(anchors)))]
        new_urls = list()
        
        for u in urls:
            if 'http' not in u:
                if u[0] != '/':
                    new_urls.append(base+'/'+u)
                else:
                    new_urls.append(base+u)
            else:
                new_urls.append(u)
        
        # Pull all the paragraph html tags
        article = soup.find_all('p')
        
        # List of the content
        content = list()
        for each in article:
            # Pulling everything between the paragraph open tag and close tag and removing blank space tags
            content.extend([r for r in re.findall(r'>(.*?)<', str(each)) if r != ''])
        # Join all seperate paragraph tags to complete the site content
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
            # Ensure that the title isn't blank
            if title == '':
                raise Exception
            # Ensure that the content isn't blank
            if content == '':
                raise Exception
        except:
            raise Exception
            pass

        url_dict = {
            'title': title,
            'content': content,
            'phone_numbers': phone_numbers,
            'date': date,
            'author': author,
            'copyright': copyright,
            'parsed': True}

    except Exception as e:
        print(e)
        url_dict = None
        new_urls = None
    
    # Make the new_url's a set to remove duplicates
    return (url_dict, new_urls)