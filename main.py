'''
WakaTime progress visualizer
'''

import re
import os
import base64
import sys
import datetime
import requests
from github import Github, GithubException

START_COMMENT = '<!--START_SECTION:waka-->'
END_COMMENT = '<!--END_SECTION:waka-->'
GRAPH_LENGTH = 25
listReg = f"{START_COMMENT}[\\s\\S]+{END_COMMENT}"

repository = os.getenv('INPUT_REPOSITORY')
waka_key = os.getenv('INPUT_WAKATIME_API_KEY')
api_base_url = os.getenv('INPUT_API_BASE_URL')
ghtoken = os.getenv('INPUT_GH_TOKEN')
show_title = os.getenv("INPUT_SHOW_TITLE")
commit_message = os.getenv("INPUT_COMMIT_MESSAGE")
blocks = os.getenv("INPUT_BLOCKS")


def this_week() -> str:
    '''Returns a week streak'''
    week_end = datetime.datetime.today() - datetime.timedelta(days=1)
    week_start = week_end - datetime.timedelta(days=6)
    print("Week header created")
    return f"Week: {week_start.strftime('%d %B, %Y')} - {week_end.strftime('%d %B, %Y')}"


def make_graph(percent: float, blocks: str) -> str:
    '''Make progress graph from API graph'''
    if len(blocks) < 2:
        raise "The BLOCKS need to have at least two characters."
    divs = len(blocks) - 1
    graph = blocks[-1] * int(percent / 100 * GRAPH_LENGTH + 0.5 / divs)
    remainder_block = int((percent / 100 * GRAPH_LENGTH - len(graph)) * divs + 0.5)
    if remainder_block > 0:
        graph += blocks[remainder_block]
    graph += blocks[0] * (GRAPH_LENGTH - len(graph))
    return graph


def get_stats() -> str:
    '''Gets API data and returns markdown progress'''
    encoded_key: str = str(base64.b64encode(waka_key.encode('utf-8')), 'utf-8')
    # last_7_days 包含今天，使用下面的方式去掉今天统计
    today = datetime.date.today()
    start = str(today - datetime.timedelta(days=7))
    end = str(today - datetime.timedelta(days=1))
    param = "start=" + start + "&end=" + end
    data = requests.get(
        f"{api_base_url.rstrip('/')}/v1/users/current/summaries?"+param,
        headers={
            "Authorization": f"Basic {encoded_key}"
        }).json()
    try:        
        return generate_table(data)
        # lang_data = data['data']['human_readable_total']
        # if 1==1:            
            # return '```text\n'+this_week()+'\n\n'+lang_data+'\n```'
            # return '```text\n Total coding time in the last 7 days :  '+lang_data+'\n```'
            # return '<center><code>Total coding time in the last 7 days :  '+lang_data+'</code></center>'
            # return '<p align="center"><code>Total coding time in the last 7 days :  '+lang_data+'</code></p>'
    except KeyError:
        print("Please Add your WakaTime API Key to the Repository Secrets")
        sys.exit(1)


    data_list = []
    try:
        pad = len(max([l['name'] for l in lang_data[:5]], key=len))
    except ValueError:
        print("The Data seems to be empty. Please wait for a day for the data to be filled in.")
        return '```text\nNo Activity tracked this Week\n```'
    for lang in lang_data[:5]:
        if lang['hours'] == 0 and lang['minutes'] == 0:
            continue
        lth = len(lang['name'])
        ln_text = len(lang['text'])
        # following line provides a neat finish
        fmt_percent = format(lang['percent'], '0.2f').zfill(5)
        data_list.append(
            f"{lang['name']}{' '*(pad + 3 - lth)}{lang['text']}{' '*(16 - ln_text)}{make_graph(lang['percent'], blocks)}   {fmt_percent} % ")
    print("Graph Generated")
    data = '\n'.join(data_list)
    if show_title == 'true':
        print("Stats with Weeks in Title Generated")
        return '```text\n'+this_week()+'\n\n'+data+'\n```'
    else:
        print("Usual Stats Generated")
        return '```text\n'+data+'\n```'

def generate_table(data) -> str:
    table_str = '<table border="1" cellspacing="0" cellpadding="20" align="center">'
    table_str += '<tbody>'
    table_str += '<tr align="center"><td colspan=7>Total coding time in the last 7 days : ' + data['cummulative_total']['text'] + '</td></tr>'
    # 定义两行展示数据 
    tr1 = '<tr>'
    tr2 = '<tr>'
    for item in data['data']:
        tr1 += '<td>' + item['range']['date'] + '</td>'
        tr2 += '<td>' + item['grand_total']['text'] + '</td>'
    tr1 += '</tr>'
    tr2 += '</tr>'
    table_str += tr1 + tr2
    table_str += '</tbody>'
    table_str += '</table>'
    print(table_str)
    print(datetime.datetime.today())
    return table_str


def decode_readme(data: str) -> str:
    '''Decode the contents of old readme'''
    decoded_bytes = base64.b64decode(data)
    return str(decoded_bytes, 'utf-8')


def generate_new_readme(stats: str, readme: str) -> str:
    '''Generate a new Readme.md'''
    stats_in_readme = f"{START_COMMENT}\n{stats}\n{END_COMMENT}"
    return re.sub(listReg, stats_in_readme, readme)


if __name__ == '__main__':
    g = Github(ghtoken)
    try:
        repo = g.get_repo(repository)
    except GithubException:
        print("Authentication Error. Try saving a GitHub Token in your Repo Secrets or Use the GitHub Actions Token, which is automatically used by the action.")
        sys.exit(1)
    if len(blocks) < 1:
        print("Invalid blocks string. Please provide a string with 2 or more characters. Eg. '░▒▓█'")
        sys.exit(1)
    contents = repo.get_readme()
    waka_stats = get_stats()
    rdmd = decode_readme(contents.content)
    new_readme = generate_new_readme(stats=waka_stats, readme=rdmd)
    if new_readme != rdmd:
        repo.update_file(path=contents.path, message=commit_message,
                         content=new_readme, sha=contents.sha)
