/** @type {import('@maizzle/framework').Config} */
module.exports = {
  build: {
    content: ["src/templates/**/*.html"],
    static: {
      source: ["src/images/**/*"],
      destination: "images",
    },
  },
  css: {
    inline: true,
    purge: false,
  },
  prettify: true,
  locals: {
    company: {
      name: "Merkle",
      address: "Columbia, Maryland, USA",
      year: new Date().getFullYear(),
    },
  },
};
