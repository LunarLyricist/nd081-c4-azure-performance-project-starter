from flask import Flask, request, render_template
import os
import redis
import socket
import sys
import logging
from datetime import datetime
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.metrics_exporter import new_metrics_exporter
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer

# App Insights
# Import required libraries for App Insights
from opencensus.ext.azure import metrics_exporter

# Define your Application Insights instrumentation key
instrumentation_key = 'InstrumentationKey=2ce3cb18-8e3a-4dbe-9e6b-e9c6765a6294'

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(connection_string=instrumentation_key))
logger.setLevel(logging.INFO)

# Metrics
exporter = new_metrics_exporter(connection_string=instrumentation_key)

# Tracing
trace_exporter = AzureExporter(connection_string=instrumentation_key)
tracer = Tracer(exporter=trace_exporter, sampler=ProbabilitySampler(1.0))

app = Flask(__name__)

# Requests
middleware = FlaskMiddleware(
    app,
    exporter=trace_exporter,
    sampler=ProbabilitySampler(1.0),
)

# Load configurations from environment or config file
app.config.from_pyfile('config_file.cfg')

if "VOTE1VALUE" in os.environ and os.environ['VOTE1VALUE']:
    button1 = os.environ['VOTE1VALUE']
else:
    button1 = app.config['VOTE1VALUE']

if "VOTE2VALUE" in os.environ and os.environ['VOTE2VALUE']:
    button2 = os.environ['VOTE2VALUE']
else:
    button2 = app.config['VOTE2VALUE']

if "TITLE" in os.environ and os.environ['TITLE']:
    title = os.environ['TITLE']
else:
    title = app.config['TITLE']

# Redis Connection
#r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=5)
r = redis.Redis()

# Check Redis connection
try:
    r.ping()
    print("Connected to Redis")
except redis.ConnectionError:
    print("Redis server is not running. Please start the Redis server and try again.")
    sys.exit(1)

# Change title to host name to demo NLB
if app.config['SHOWHOST'] == "true":
    title = socket.gethostname()

# Init Redis
try:
    if not r.get(button1): r.set(button1, 0)
    if not r.get(button2): r.set(button2, 0)
except redis.ConnectionError as e:
    print(f"Error initializing Redis: {e}")
    sys.exit(1)

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        if request.method == 'GET':
            # Get current values
            vote1 = r.get(button1).decode('utf-8')
            vote2 = r.get(button2).decode('utf-8')

            # Trace cat and dog votes
            with tracer.span(name='cat_vote'):
                pass
            with tracer.span(name='dog_vote'):
                pass

            # Return index with values
            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

        elif request.method == 'POST':

            if request.form['vote'] == 'reset':
                # Empty table and return results
                r.set(button1, 0)
                r.set(button2, 0)
                vote1 = r.get(button1).decode('utf-8')
                properties = {'custom_dimensions': {'Cats Vote': vote1}}
                # Log cat vote
                logger.info('Cats vote reset', extra=properties)

                vote2 = r.get(button2).decode('utf-8')
                properties = {'custom_dimensions': {'Dogs Vote': vote2}}
                # Log dog vote
                logger.info('Dogs vote reset', extra=properties)

                return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

            else:
                # Insert vote result into DB
                vote = request.form['vote']
                r.incr(vote, 1)

                # Get current values
                vote1 = r.get(button1).decode('utf-8')
                vote2 = r.get(button2).decode('utf-8')

                # Return results
                return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return "Internal Server Error", 500

if __name__ == "__main__":
    # Use the statement below when running locally
    # app.run(debug=True)
    # Use the statement below before deployment to VMSS
    app.run(host='0.0.0.0', threaded=True, debug=True) # remote
