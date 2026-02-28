/** @type {import('@maizzle/framework').Config} */
module.exports = {
  build: {
    content: ["src/templates/**/*.html"],
    output: {
      path: "build_production",
    },
  },
  css: {
    inline: true,
    purge: true,
  },
  prettify: false,
  minify: {
    collapseWhitespace: true,
    removeComments: true,
  },
};
