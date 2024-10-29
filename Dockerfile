FROM python:3.11
LABEL maintainer="dlaine@linagora.com"

ENV PYTHONUNBUFFERED TRUE
ENV SERVICE_TYPE=llm_gateway \
    TEMP=/tmp \
    PYTHONPATH=/usr/src

# Set the working directory in the container
WORKDIR /usr/src/

# Install dependencies
# Copy the requirements file first to leverage Docker cache
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install spacy model
RUN python3 -m spacy download fr_core_news_sm
# Copy the code of your application
COPY . /usr/src

# Make sure scripts are executable
RUN chmod +x ./scripts/healthcheck.sh \
    && chmod +x ./scripts/wait-for-it.sh\
    && chmod +x ./scripts/start.sh 
# Extract version from RELEASE.md and set it as an environment variable
RUN VERSION=$(grep '^#' RELEASE.md | head -1 | cut -d '#' -f 2 | xargs) \
    && echo "VERSION=$VERSION" > .env


# Healthcheck
HEALTHCHECK CMD ./scripts/healthcheck.sh

# Define the entry point
#ENTRYPOINT ["python", "-Xfrozen_modules=off"]
CMD ["scripts/start.sh"]