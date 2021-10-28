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

def crawl_url(target: str, kwargs, extra_cols=None, reparse=False, cutoff=None):
    '''Specify target url to start a crawl and what BeautifulSoup Function you'd like to have run looking for
    content, you must pass the kwargs to the sub function
    '''
    # list of the invalid_urls
    invalid_urls = []
    # Base web url from target
    base = re.match(r'^.*(?:com|org|gov|net|us|eu|tv|me|.co)', target)[0]
    # extract only the base site from target
    site = re.findall(r'^https?://?(.*?)\.', base)[0]
    filename = site+'_scraped_data.csv'
    # Default dict
    def_dict = {'title': 'None', 'content': 'None', 'parsed': False}
    if extra_cols:
        for key in extra_cols.keys():
            def_dict[key] = 'None'
    
    # Check if there is a file for that site
    if os.path.exists(filename):
        # Pull the dataframe in
        df = pd.read_csv(filename, index_col='url')
        # check if the target is in the dataframe
        if reparse:
            df.loc[target, 'parsed'] = False
            
        elif target not in df.index.to_list():
            # Add target to the dataframe
            df.loc[target] = def_dict
            
    else:
        # If the dataframe does not exist, set the first value to the target
        # Set the url to the target
        def_dict['url'] = target
        df = pd.DataFrame([def_dict]).set_index('url')
            
    # Ensures there are no more urls to parse
    while len(df[~df.parsed].parsed.to_list()) != 0 and df[df.parsed].shape[0] < cutoff:
        # Pull the dataframe in again to ensure it's fresh each iteration
        if os.path.exists(filename):
        # Pull the dataframe in if it's not the first time
            if reparse:
                df.loc[target, 'parsed'] = False
                reparse = False
                
            elif target not in df.index.to_list():
                # Add target to the dataframe
                df.loc[target] = def_dict
            
        # Set the url to parse as the first element in the list
        url = df[~df.parsed].index[0]

        # Returns either None or a tuple containing the (url_dict, new_urls)
        valid = parse_target_data(url, kwargs, extra_cols)
        
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

    
    print('Finshed All Combinations')        
    return df

def scrape_for_more_urls(soup, base):
    '''Parses anchors'''
    # Fetches all anchors from page
    anchors = soup.find_all('a')

    # Pulls all hyperlinks from the anchors
    regex = r'''<a\s+(?:[^>]*?\s+)?href="(.*?)"'''
    
    # checks if the urls have http in them or not and concats with base if not to test
    try:
        tmp_urls = list(set(re.findall(regex, str(anchors))))
        urls = [u for u in tmp_urls if u not in ['', ' ']]
        new_urls = list()
    
        for u in urls:
            # Checks to see if http is in the url
            if 'http' not in u:
                # Checks to see if the first spot is a /
                if u[0] != '/':
                    # If not it concats the base url with the / and the url
                    new_urls.append(base+'/'+u)
                else:
                    # Otherwise just the base url with the url
                    new_urls.append(base+u)
            else:
                # Add the normal url
                new_urls.append(u)

        # If there are not any urls referenced on the site
    except:
            return(list())
    
    # Returns a unique url list
    return list(set(new_urls))

def extract_content(soup, kwargs):
    '''Takes a BeautifulSoup Response and scapes it for all text with BeautifulSoup find function
    '''

    article = soup.find_all(**kwargs)
    
    # List of the content
    content = list()
    for each in article:
        # Pulling everything between the paragraph open tag and close tag and removing blank space tags
        try:
            content.extend([r for r in re.findall(r'>(.*?)<', str(each)) if r != ''])
        # If content is blank
        except:
            content.extend('')

    # Join all seperate paragraph tags to complete the site content
    content = ''.join(content)
    return content

def extract_title(soup):
    ''' Takes a BeautifulSoup response and extracts the title
    '''
    try:
        # Returns title as string
        return soup.title.string
    except:

        return ''

def parse_target_data(url, kwargs, extra_cols=None, base=None, headers={'User-Agent': 'Codeup Data Science'}):
    '''the url is the target and the kwargs is the default 'content' key and extra_cols 
    needs to be defined like this:
    {'some_new_column_name': {'name': ''__tag__', '__some_html_tag__': '__searchvalue'}}
    '''
    if not base:
        base = re.match(r'^.*(?:com|org|gov|net|us|eu|tv|me|.co)', url)[0]
    try:
        response = get(url, headers=headers)
        # If there is a error response and no_blanks are desired
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Fetches content from the tag you'd like
        ## Specify the tag here!
        content = extract_content(soup, kwargs)

    except Exception as e:
        print(e)
        return (None, None)
    
    url_dict = {
            'title': extract_title(soup),
            'content': content,
            'parsed': True}

    # Fetch addtional content
    if extra_cols:
        for key, value in extra_cols.items():
            url_dict[key] = extract_content(soup, value)

    # Fetches all urls
    new_urls = scrape_for_more_urls(soup, base)
    return (url_dict, new_urls)

def get_news_articles(cutoff=500):
    '''Pass cutoff values to get news articles and if csv already exists will return it
    '''
    # Set default filename
    filename = 'news_articles.csv'

    #Check if the file already exists
    if os.path.exists(filename):
        # Read the csv and define the index to be the url
        df = pd.read_csv(filename, index_col='url')
        # Check to see if the df is at least the cutoff length
        if df.shape >= cutoff:
            return df
    
    # Default url, can change if it becomes broken
    inshorts_url = 'https://inshorts.com/en/news/airstrike-hits-capital-of-ethiopias-tigray-3-killed-report-1635433206925'

    # The names of the columns you'd like go in keys and the searching parameters go into the values 
    extra_cols = {
    'news_articles' : {'name': 'div', 'itemprop':'articleBody'},
    'author': {'class': 'author'},
    'date': {'class': 'date'}
    }

    # The kwargs will be put into the content columns
    df = crawl_url(inshorts_url, kwargs = {'name': 'p'}, extra_cols=extra_cols, cutoff=cutoff)

    # Split the title because it contains the category within the title
    df['category'] = df.title.apply(lambda x: x.split('|')[1])
    df.to_csv(filename)

    return df

    

