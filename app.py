import re
import plotly.utils
import requests
from flask import Flask, render_template, request
import plotly.graph_objs as go
import json
from tweet_sentiment_analysis import get_sentiment_score

app = Flask(__name__)

AWS_IP = '3.144.167.111'
AWS_PORT = '8983'
SOLR_CORE_NAME = 'IR_P4'
inp_query = ""



@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/overview')
def overview():
    query_calc = 'http://' + AWS_IP + ':' + AWS_PORT + '/solr/' + SOLR_CORE_NAME + '/select?q=*%3A*&rows=90349'
    query_poi = 'http://' + AWS_IP + ':' + AWS_PORT + '/solr/' + SOLR_CORE_NAME + '/select?q=poi_name%3A*&rows=90349'
    json_file = requests.get(query_calc).json()
    poi_json = requests.get(query_poi).json()
    hi = 0
    en = 0
    ind_sent = [0, 0, 0, 0]  # pos,neg,neu,mix
    mex_sent = [0, 0, 0, 0]
    us_sent = [0, 0, 0, 0]
    es = 0
    dates = dict()
    poi = dict()
    for i in poi_json["response"]["docs"]:
        if i["poi_name"] not in poi.keys():
            poi[i["poi_name"]] = 0
        else:
            poi[i["poi_name"]] += 1

    for i in json_file["response"]["docs"]:
        date = i["tweet_date"][8:10] + "-" + i["tweet_date"][5:7] + "-" + i["tweet_date"][0:4]
        if date not in dates.keys():
            dates[date] = 0
        else:
            dates[date] += 1
        if "country" not in i.keys():
            pass
        else:
            if i["country"] == "India":
                if i["sentiment"] == "POSITIVE":
                    ind_sent[0] += 1
                elif i["sentiment"] == "NEGATIVE":
                    ind_sent[1] += 1
                elif i["sentiment"] == "NEUTRAL":
                    ind_sent[2] += 1
                else:
                    ind_sent[3] += 1
            elif i["country"] == "USA":
                if i["sentiment"] == "POSITIVE":
                    us_sent[0] += 1
                elif i["sentiment"] == "NEGATIVE":
                    us_sent[1] += 1
                elif i["sentiment"] == "NEUTRAL":
                    us_sent[2] += 1
                else:
                    us_sent[3] += 1
            else:
                if i["sentiment"] == "POSITIVE":
                    mex_sent[0] += 1
                elif i["sentiment"] == "NEGATIVE":
                    mex_sent[1] += 1
                elif i["sentiment"] == "NEUTRAL":
                    mex_sent[2] += 1
                else:
                    mex_sent[3] += 1
        if i["tweet_lang"] == "en":
            en += 1
        elif i["tweet_lang"] == "es":
            es += 1
        else:
            hi += 1
    l = []
    for keys in dates:
        l.append((keys, dates[keys]))
    lab = [row[0] for row in l]
    val = [row[1] for row in l]

    fig = go.Figure()
    trace = go.Bar(x=[en, es, hi], y=['English', 'Spanish', 'Hindi'], orientation='h', opacity=0.7)
    data = [trace]
    langJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    trace1 = go.Pie(labels=['Positive', 'Negative', 'Neutral', 'Mixed'],
                    values=[ind_sent[0], ind_sent[1], ind_sent[2], ind_sent[3]])
    data1 = [trace1]
    country_sent_ind = json.dumps(data1, cls=plotly.utils.PlotlyJSONEncoder)

    trace2 = go.Pie(labels=['Positive', 'Negative', 'Neutral', 'Mixed'],
                    values=[us_sent[0], us_sent[1], us_sent[2], us_sent[3]])
    data2 = [trace2]
    country_sent_us = json.dumps(data2, cls=plotly.utils.PlotlyJSONEncoder)

    trace3 = go.Pie(labels=['Positive', 'Negative', 'Neutral', 'Mixed'],
                    values=[mex_sent[0], mex_sent[1], mex_sent[2], mex_sent[3]])
    data3 = [trace3]
    country_sent_mex = json.dumps(data3, cls=plotly.utils.PlotlyJSONEncoder)

    trace4 = go.Pie(labels=["India", "Mexico", "USA"], values=[ind_sent[0] + ind_sent[1] + ind_sent[2] + ind_sent[3],
                                                               mex_sent[0] + mex_sent[1] + mex_sent[2] + mex_sent[3],
                                                               us_sent[0] + us_sent[1] + us_sent[2] + us_sent[3]])
    data4 = [trace4]
    country_tweet = json.dumps(data4, cls=plotly.utils.PlotlyJSONEncoder)
    trace5 = go.Bar(x=list(poi.values()), y=list(poi.keys()), orientation='h', opacity=0.7)
    data5 = [trace5]
    poi_tweet = json.dumps(data5, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('overview.html', langJSON=langJSON, country_sent_ind=country_sent_ind,
                           country_sent_us=country_sent_us, country_sent_mex=country_sent_mex, dates=lab, val=val,
                           country_tweet=country_tweet, poi_tweet=poi_tweet)


@app.route('/tweet_search', methods=['POST', 'GET'])
def tweetsearch():
    global inp_query
    poi_name,cntry, lang = "","",""
    input_query = request.args.get('query')
    if input_query!=None:
        inp_query = input_query
    else:
        input_query = inp_query
    poi_part = ""
    cntry_part = ""
    lang_part = ""
    if request.method == "POST":
        # input_query = "Hi"
        poi_name = request.form.get('POI')
        cntry = request.form.get('country')
        lang = request.form.get('lang')
        if poi_name!="All" and poi_name is not None:
            poi_part = '&fq=poi_name%3A('+poi_name+')'
        if cntry!="All" and cntry is not None:
            cntry_part = '&q=country%3A('+cntry+')'
        if lang!="All" and lang is not None:
            lang_part = '&fq=tweet_lang%3A('+lang+')'
        print(input_query,poi_name, cntry, lang)
        print("got here", input_query, poi_part, cntry_part, lang_part)

    if input_query is None or input_query == '':
        print('rendering basic page')
        return render_template('basic_page.html')
    encoded_query = preprocess(input_query)
    fig = go.Figure()
    query_url = 'http://' + AWS_IP + ':' + AWS_PORT + '/solr/' + SOLR_CORE_NAME + '/select?fl=id%20score%20tweet_text%20sentiment%20sentiment_score&q=text_en%3A(' + encoded_query + ')%20or%20text_hi%3A(' + encoded_query + ')%20or%20tweet_text%3A(' + encoded_query + ')%20or%20text_es%3A(' + encoded_query + ')'+poi_part+lang_part+cntry_part+'&rows=50'
    query_sent='http://' + AWS_IP + ':' + AWS_PORT + '/solr/' + SOLR_CORE_NAME + '/select?fl=id%20score%20tweet_text%20sentiment%20sentiment_score&q=text_en%3A(' + encoded_query + ')%20or%20text_hi%3A(' + encoded_query + ')%20or%20tweet_text%3A(' + encoded_query + ')%20or%20text_es%3A(' + encoded_query + ')'+poi_part+lang_part+cntry_part+'&rows=58000'
    query_calc='http://' + AWS_IP + ':' + AWS_PORT + '/solr/' + SOLR_CORE_NAME + '/select?q=text_en%3A(' + encoded_query + ')%20or%20tweet_text%3A(' + encoded_query + ')%20or%20text_hi%3A(' + encoded_query + ')%20or%20text_es%3A(' + encoded_query + ')'+poi_part+lang_part+cntry_part+'&rows=58000'
    print(query_url)
    data = requests.get(query_url).json()
    data1 = requests.get(query_calc).json()
    total_lang = 0
    total_hi = 0
    total_en = 0
    total_es = 0
    neutral = 0
    pos = 0
    neg = 0
    mix = 0
    tot = 0
    poi = dict()
    for i in data1['response']['docs']:
        if "poi_name" in i:
            if i["poi_name"] not in poi.keys():
                poi[i["poi_name"]] = 0
            else:
                poi[i["poi_name"]] += 1
        tweet_lang = i['tweet_lang']
        total_lang += 1
        if tweet_lang == 'hi':
            total_hi += 1
        elif tweet_lang == 'en':
            total_en += 1
        else:
            total_es += 1
        sentiment = i['sentiment']
        tot += 1
        if sentiment == 'NEUTRAL':
            neutral += 1
        elif sentiment == 'MIXED':
            mix += 1
        elif sentiment == 'POSITIVE':
            pos += 1
        else:
            neg += 1
    docs = {}
    graphJSON = {}
    langJSON = {}
    poi_tweet = {}
    if tot > 0:
        neg_per = ((neg / tot) * 100)
        pos_per = ((pos / tot) * 100)
        mix_per = ((mix / tot) * 100)
        neu_per = ((neutral / tot) * 100)
        trace2 = go.Pie(labels=['English', 'Spanish', 'Hindi'], values=[total_en, total_es, total_hi])
        data3 = [trace2]
        langJSON = json.dumps(data3, cls=plotly.utils.PlotlyJSONEncoder)
        trace1 = go.Pie(labels=['Negative', 'Positive', 'Mixed', 'Neutral'], values=[neg_per, pos_per, mix_per, neu_per])
        data2 = [trace1]
        graphJSON = json.dumps(data2, cls=plotly.utils.PlotlyJSONEncoder)
        docs = data['response']['docs']
        trace5 = go.Bar(x=list(poi.keys()), y=list(poi.values()), orientation='v', opacity=0.7)
        data5 = [trace5]
        poi_tweet = json.dumps(data5, cls=plotly.utils.PlotlyJSONEncoder)
    """text=[]
    for i in docs:
        text.append(i["tweet_text"])"""
    news_docs = tweetnews(input_query)
    print("here now", input_query)

    if request.method == "POST":
        return render_template('basic_page.html', query = input_query, poi=poi_name, cntry = cntry, lang = lang, tweet_search=docs, tweet_news=news_docs, graphJSON=graphJSON,
                           langJSON=langJSON, poi_tweet=poi_tweet)

    return render_template('basic_page.html', query = input_query, poi=poi_name, cntry = cntry, lang = lang, tweet_search=docs, tweet_news=news_docs, graphJSON=graphJSON,
                           langJSON=langJSON, poi_tweet=poi_tweet)


def tweetnews(query):
    news_docs_20 = []
    query = preprocess(query)
    try:
        input_query = query
        encoded_query = preprocess(input_query)
        news_query_url = 'https://newsapi.org/v2/everything?q=' + encoded_query + '&sortBy=publishedAt&apiKey=ae9778d05cd74f219e4fcaf7afad1c3a'
        news_data = requests.get(news_query_url).json()
        news_docs = news_data['articles'][:40]
        for article in news_docs:
            description = article.get('description')
            sentiment, sentiment_score = get_sentiment_score(description)
            article['sentiment'] = sentiment
            article['sentiment_score'] = sentiment_score
            news_docs_20.append(article)
    except Exception as e:
        print(e)
    return news_docs_20


def preprocess(query):
    query = re.sub(r'[^\w\s]', '', query)
    query = query.strip('\n').replace(':', '')
    return query


@app.route('/')
def hello():
    return render_template('index.html')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
