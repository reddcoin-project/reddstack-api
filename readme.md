## Reddstack Web Interface

This package contains the web interface for Reddstack Server. It talks to the Reddstack server and provides an interface for creating and managing names in decentralized namespaces and database tables on the blockchain

## Installation
Installing this package and required dependencies

### Debian + Ubuntu

Download the source from github

```
$ git clone https://github.com/reddink/reddstack-web
```

Ideally you will install reddstack-web into a virtual environment


```
$ [sudo] pip install virtualenv
$ cd reddstack-web
$ virtualenv venv
$ source venv/bin/activate
```

Install dependencies (via pip:)

```
$ pip install pybitcoin
$ pip install Flask
$ pip install flask-cors
$ pip install Flask-WTF
```

This will download the latest internal dependencies to the virtual environment

## Usage

Start application

```
./run.py
```

Reddstack-web is listening on all interfaces, port 8080.  
Launch from your favourite browser

```
http://localhost:8080
```

