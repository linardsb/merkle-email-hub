FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install --production

COPY scripts/ ./scripts/
COPY postcss-email-optimize.js ./
COPY precompiled-detect.js ./
COPY mjml-compile.js ./
COPY index.js ./
COPY data/ ./data/

EXPOSE 3001

USER node

CMD ["node", "index.js"]
