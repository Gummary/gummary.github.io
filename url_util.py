import requests
from bs4 import BeautifulSoup
import re


pattern = re.compile("([0-9]+)\. (http[s]?://.*)")
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'}

def get_title(url:str):
	proxies = {
		# 'http':'http://127.0.0.1:7890',
		# 'https':'https://127.0.0.1:7890'
	}
	try:
		res = requests.get(url, proxies=proxies, headers=headers)
	except requests.exceptions.SSLError:
		return None
	except requests.exceptions.ProxyError:
		return None
	if res.status_code != 200:
		return None
	res.encoding = 'utf-8'
	soup = BeautifulSoup(res.text, 'lxml')
	if soup is None or soup.title is None:
		return None
	return soup.title.text

def replace_reference_url(refer):
	match = pattern.match(refer)
	url = match.group(2)
	title = get_title(url)
	if title is None:
		title = input("Please input title for {}\n".format(url)).strip()
	md_url = "[{}]({})".format(title, url)
	rep = lambda m: "{}. {}".format(m.group(1), md_url)
	return re.sub(pattern, rep, refer)


def replace_urls_in_reference(post):
	article = []
	for line in open(post, encoding='utf-8'):
		if pattern.match(line) is None:
			article.append(line)	
			continue
		new_refer = replace_reference_url(line)
		print(new_refer)
		article.append(new_refer)
	return article

post_path = input("Please input markdown file:\n")
article = replace_urls_in_reference(post_path)
with open(post_path, "w", encoding='utf-8') as f:
	f.write("".join(article))