FROM ubuntu:20.04

ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install required packages
RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install -y --no-install-recommends \
    python3.8 \
    python3.8-venv \
    python3-pip \
    wget \
    gnupg \
    unzip \
  && apt-get clean \
  && find / -type d -name __pycache__ -exec rm -rf {} +

# Create virtualenv
ENV VIRTUAL_ENV=/opt/scrapy
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python3.8 -m venv $VIRTUAL_ENV \
  && pip install --no-cache-dir --upgrade pip setuptools \
  && find / -type d -name __pycache__ -exec rm -rf {} +

# Install scrapy
COPY requirements.txt $VIRTUAL_ENV/requirements.txt
RUN apt-get install -y --no-install-recommends build-essential python3.8-dev \
  && pip install --no-compile --no-cache-dir -r $VIRTUAL_ENV/requirements.txt \
  && apt-get autoremove -y build-essential python3.8-dev \
  && apt-get clean \
  && find / -type d -name __pycache__ -exec rm -rf {} +

# Install google-chrome & chromedriver
ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1
RUN wget -qO - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends google-chrome-stable \
  && apt-get clean
RUN wget -qO /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/`wget -qO - https://chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip \
  && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin \
  && rm -f /tmp/chromedriver.zip

# Add scrapy user
RUN useradd -m scrapy
USER scrapy:scrapy
WORKDIR /home/scrapy

# Copy spiders
COPY --chown=scrapy:scrapy netkeiba/ /home/scrapy/netkeiba/
COPY --chown=scrapy:scrapy scrapy.cfg /home/scrapy/scrapy.cfg
