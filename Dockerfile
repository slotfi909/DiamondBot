FROM python:3.12-slim-bullseye

WORKDIR /app

ENV LANG C.UTF-8

ENV LC_ALL C.UTF-8

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONFAULTHANDLER=1

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY prisma/ ./prisma/

RUN prisma generate

COPY ./ ./

RUN chmod +x run_bot.bash

ENV MODE=production

ENV WEBHOOK_PORT=8443

EXPOSE 8443

CMD [ "./run_bot.bash" ]
