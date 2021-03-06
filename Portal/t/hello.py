#coding=utf-8

from flask import Flask,url_for,request,render_template,redirect,abort,escape,session
app = Flask(__name__)

@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)
    
if __name__ == "__main__":
    app.run(debug=True)