import os
import math
import yfinance as yf
import openai
from flask import Flask, redirect, render_template, request, url_for, session
import time
from twilio.rest import Client
from pymongo import MongoClient
import cohere
from cohere.responses.classify import Example


# cohere api credentials
cohere_key = "9Hw5PqZQkno7XVDaKzMEwEttVZVze3CsNfpGH8qV"
co = cohere.Client(cohere_key)

# twilio api credentials
account_sid = "AC19c5185f5a78f8792fe1b5bcb64db168"
auth_token = "b8a660f38f828fbff50da9f2348647dc"
client = Client(account_sid, auth_token)

# mongodb connections
cluster = "mongodb+srv://aryan527:1234@cluster0.p84jhqr.mongodb.net/?retryWrites=true&w=majority"
mongo_client = MongoClient(cluster)
db = mongo_client.userInfo
userInfo = db.userInfo



# flask connection
app = Flask(__name__)
app.secret_key = "Hehe1234"

# openai api key
openai.api_key = "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"


@app.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        bank_name = request.form["bank_name"]
        response1 = openai.Completion.create(
            model="text-davinci-003",
            prompt=generate_prompt1(bank_name),
            temperature=0,
        )
        response2 = openai.Completion.create(
            model="text-davinci-003",
            prompt=generate_prompt2(bank_name),
            temperature=0,
        )

        response = response1.choices[0].text[:-1] + ', '

        response2 = response2.choices[0].text
        response2 = response2[0:]
        response += response2
        print(response)
        health = generate_health(response)[0]
        type = generate_health(response)[1]

        return redirect(url_for("investment", result =health, bank_type =type))

    result = request.args.get("result")
    bank_type = request.args.get("bank_type")  
    return render_template("index.html", result=result, bank_type = bank_type)


@app.route("/investment")
def investment():
    result = request.args.get("result")
    bank_type = request.args.get("bank_type")
    # render the result page with the result and bank_type
    return render_template("investment.html", result=result, bank_type=bank_type)


@app.route("/signup", methods=("GET", "POST"))
def signup():
    if request.method == "POST":
        phone_number = request.form["phone-number"]
        status = request.args.get("status")
        
        print(send_otp(phone_number))

        return redirect(url_for("verify", phone = phone_number, status = status))



    # render the third page
    return render_template("signup.html")


@app.route("/verify", methods=("GET", "POST"))
def verify():
    if request.method == "POST":
        otp = request.form["phone-number"]
        
        phone = session.get("old-phone")
        
        status = verify_otp(phone, otp) if phone != None else 0
        session["login-status"] = status

        # check if already a user
        exists = False
        res = userInfo.find({"phone": phone})
        for r in res:
            if r["phone"] == phone:
                exists = True
                
        # add if doesnt exist
        if not exists:
            data = {"phone": phone, "favs": []}
            userInfo.insert_one(data)

        return redirect(url_for("verify", phone = phone, status = status))

    phone = request.args.get("phone")
    session["old-phone"] = phone
    status = request.args.get("status")
    return render_template("verify.html", phone = phone, status = status)


@app.route("/favorites", methods = ("GET", "POST"))
def favorites():
    if request.method == "POST":
        if session.get("login-status") == "approved":
            bank_name = request.form["bankName"]
            if bank_name != None and bank_name != "":
                
                phone_number = session.get("old-phone")

                # length of favorites list from database ()
                fav_list = (userInfo.find_one({"phone": phone_number}))["favs"]
                num_fav = len(fav_list)

                if num_fav < 3:
                    # add bank_name to favorites
                    if bank_name not in fav_list:
                        fav_list.append(bank_name)
                        userInfo.update_one({"phone": phone_number}, {"$set": {"favs": fav_list}})
                        num_fav = len(fav_list)



        return redirect(url_for("favorites", length = num_fav, fav_list = fav_list))

    fav_list = (userInfo.find_one({"phone": session.get("old-phone")}))["favs"]
    length = len(fav_list)

    return render_template("favorites.html", length=length, fav_list = fav_list)


@app.route("/account")
def account():
    
    phone = session.get("old-phone")

    
    if phone != None:
        fav_list = userInfo.find_one({"phone": phone})["favs"]    
    else:
        fav_list = request.args.get("fav_list")

    return render_template("account.html", phone = phone, fav_list = fav_list)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/faq", methods = ("GET", "POST"))
def faq():
    if request.method == "POST":

        prompt = request.form["faq"]
        answer = get_answer(prompt)
        
        return redirect(url_for("faq", answer=answer))

    answer = request.args.get("answer")
    return render_template("faq.html", answer=answer)

def generate_prompt1(bank_name):
    result1 = """Give the data list [CAR, Net income, loan-to-deposit ratio, Liquidity ratio, asset quality, Deposit market share, average stock price] for {} 2021 in the following format:

Bank: Bank of America (2021)

Data:
[CAR, Net income, loan-to-deposit ratio, Liquidity ratio]

list: [13.9, 45.1, 76, 1.35,


Bank: Morgan Stanley (2021)

Data:
[CAR, Net income, loan-to-deposit ratio, Liquidity ratio]

list: [14.8, 16.9, 91, 1.28,


Bank: {} (2021)

Data:
[CAR, Net income, loan-to-deposit ratio, Liquidity ratio]

list: 
""".format(
        bank_name.capitalize(), bank_name.capitalize()
    )

    time.sleep(11)

    
    
    return result1

def generate_prompt2(bank_name):
    result2 = """Give the data list [CAR, Net income, loan-to-deposit ratio, Liquidity ratio, asset quality, Deposit market share (-1 if the bank is an investment bank), average stock price] for {} 2021 in the following format:

Bank: Bank of America (2021)

Data:
[asset quality, Deposit market share, average stock price]

list:  0.32, 10, 40.68]


Bank: Morgan Stanley (2021)

Data:
[asset quality, Deposit market share, average stock price]

list:  0.48, -1, 389.07]


Bank: {} (2021)

Data:
[asset quality, Deposit market share, average stock price]

list: 
""".format(bank_name.capitalize(), bank_name.capitalize())
    
    return result2



def generate_health(data_list):
    data = [float(i) for i in data_list[1:-1].split(",")]
    car = data[0]
    net_income = data[1]
    ltd_ratio = data[2]
    liquidity = data[3]
    asset_qual = data[4]
    mkt_share = data[5]
    avg_price = data[6]

    print(str(car) + " " + str(net_income)+ " " + str(ltd_ratio)+ " " + str(liquidity)+ " " + str(asset_qual)+ " " + str(mkt_share) + " " + str(avg_price))

    # CAR value conversion out of 100
    # Min - 8%, Max - 15%, formula (CAR - min)/(max - min) * 100
    car = ((car - 8)/(6))*100
    liquidity = (math.cos((1.3-liquidity)*(math.pi/1.2)))*100
    asset_qual = ((100-asset_qual)-98)*50

    # commercial max - 429, min - 33, investment max - 647.07, min - 36.07
    if (mkt_share != -1):
        avg_price = ((avg_price-33)/396)*100
        mkt_share = ((mkt_share-4)/11)*100
        net_income = ((net_income + 1)/24)*100
        health = (car*0.2) + (net_income*0.25) + (ltd_ratio*0.1) + (liquidity*0.2) + (asset_qual*0.15) + (mkt_share*0.08) + (avg_price*0.02)
    else: 
        avg_price = ((avg_price-36.07)/404)*100
        net_income = ((net_income + 8)/22)*100
        health = (car*0.2) + (net_income*0.25) + (ltd_ratio*0.1) + (liquidity*0.2) + (asset_qual*0.15) + (avg_price*0.1)

    print(str(car) + " " + str(net_income)+ " " + str(ltd_ratio)+ " " + str(liquidity)+ " " + str(asset_qual)+ " " + str(mkt_share) + " " + str(avg_price))

    return [health if health <= 100 else 97.89, "investment" if mkt_share == -1 else "commercial"]


def send_otp(phone_number):
    verification = client.verify \
                     .v2 \
                     .services('VA59de1d735cbf39c803a1f60bf9f46928') \
                     .verifications \
                     .create(
                          to='+1' + str(phone_number),
                          channel='sms'
                      )

    v_sid = verification.sid
    return v_sid


def verify_otp(phone_number, code):
    verification_check = client.verify \
                           .v2 \
                           .services('VA59de1d735cbf39c803a1f60bf9f46928') \
                           .verification_checks \
                           .create(to='+1' + str(phone_number), code=code)

    return verification_check.status



def get_answer(prompt):

    examples=[
  Example("How can I search for different banks?", "By using the search bar"),
  Example("How do I contact you guys?", "By either sending a message on the contact message or by calling on the number given below"),
  Example("How do i select my favorite banks?", "Go to Favorites Tab"),
  Example("Is this website free to use?", "Yes"),
  Example("How can i search for investment banks?", "By using the search bar"),
  Example("How can i search for commercial banks?", "By using the search bar"),
  Example("How do I sign up", "By clicking on the sign-up button"),
  Example("How do I know whats the motto of the company?", "By clicking the About Us button"),
  Example("Where can i see the current best banks", "Top banks are displayed on the first page of the website"),
  Example("Where can i see my account information", "By clicking on the account button"),
  Example("How do i send a message to BankWise?","By either sending a message on the contact message or by calling on the number given below"),
  Example("How do i see my favorite banks?","Go to Favorites Tab"),
  Example("Will I never have to pay for it?","Yes"),
  Example("How do i login?","By clicking on the sign-up button"),
  Example("How do i get to know what's the website about?","By clicking the About Us button"),
  Example("Where can i see the best banks?","Top banks are displayed on the first page of the website"),
  Example("Where can i see my user information?","By clicking on the account button")

    ]

  


    response = co.classify(  
        model='large',  
        inputs=[prompt,],  
        examples=examples)

    return (response.classifications[0].prediction)


