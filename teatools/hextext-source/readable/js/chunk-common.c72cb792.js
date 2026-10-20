(window["webpackJsonp"] = window["webpackJsonp"] || []).push([
  ["chunk-common"],
  {
    "04ec": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a(
            "div",
            { staticClass: "postbox" },
            [
              a("h3", { staticClass: "izquierda germania white-text sh-t-2" }, [
                t._v("Comments"),
              ]),
              a(
                "div",
                { staticClass: "row" },
                [
                  t._l(t.posts, function (e, n) {
                    return a(
                      "div",
                      {
                        key: "p" + n,
                        staticClass: "col s12",
                        class: { pending: 0 == e.estado },
                      },
                      [
                        a("div", { staticClass: "post izquierda" }, [
                          a(
                            "div",
                            {
                              staticClass: "chip roboto",
                              on: {
                                click: function (a) {
                                  return t.go(e.iduser);
                                },
                              },
                            },
                            [
                              a("img", {
                                style: {
                                  backgroundImage:
                                    "url(" +
                                    t.base +
                                    "img/" +
                                    e.userpic +
                                    ".jpg)",
                                },
                                attrs: { src: "/Assets/img/cuadro.png" },
                              }),
                              t._v(
                                "\n\t\t\t\t\t    " +
                                  t._s(e.username) +
                                  "\n\t\t\t\t\t",
                              ),
                            ],
                          ),
                          e.iduser == t.user.id
                            ? a(
                                "div",
                                {
                                  staticClass: "chip roboto red-text manito",
                                  on: {
                                    click: function (a) {
                                      return t.tryDeleteCommnets(e);
                                    },
                                  },
                                },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "trash-alt" },
                                  }),
                                ],
                                1,
                              )
                            : t._e(),
                          a(
                            "p",
                            {
                              staticClass: "izquierda open",
                              staticStyle: { "word-break": "break-word" },
                            },
                            [
                              t._v(
                                "\n\t\t\t\t\t\t" +
                                  t._s(e.comentario) +
                                  "\n\t\t\t\t\t",
                              ),
                            ],
                          ),
                        ]),
                      ],
                    );
                  }),
                  a("div", { staticClass: "col s12" }, [
                    a("textarea", {
                      directives: [
                        {
                          name: "model",
                          rawName: "v-model",
                          value: t.message,
                          expression: "message",
                        },
                      ],
                      staticClass: "roboto",
                      attrs: { maxlength: "180" },
                      domProps: { value: t.message },
                      on: {
                        input: function (e) {
                          e.target.composing || (t.message = e.target.value);
                        },
                      },
                    }),
                    a(
                      "div",
                      { staticClass: "right" },
                      [
                        t._v(
                          "\n\t\t\t\t\t" +
                            t._s(t.count) +
                            "/" +
                            t._s(t.limit) +
                            "  \n\t\t\t\t\t",
                        ),
                        t.user.id
                          ? a(
                              "button",
                              {
                                staticClass: "btn new-flat",
                                on: {
                                  click: function (e) {
                                    return t.makePost();
                                  },
                                },
                              },
                              [t._v("Send")],
                            )
                          : [
                              a("span", { staticClass: "roboto" }, [
                                t._v(" Login to make a comment "),
                              ]),
                              a(
                                "span",
                                {
                                  staticClass: "mk-login",
                                  on: {
                                    click: function (e) {
                                      return t.$refs.login.open();
                                    },
                                  },
                                },
                                [t._v("Login")],
                              ),
                            ],
                      ],
                      2,
                    ),
                  ]),
                ],
                2,
              ),
              a("Login", { ref: "login" }),
            ],
            1,
          );
        },
        s = [],
        r = (a("8e6e"), a("456d"), a("ac6a"), a("bd86")),
        i = (a("c5f6"), a("2f62")),
        o = a("f8eb"),
        c = a("bc3a"),
        l = a.n(c),
        u = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a(
            "div",
            { staticClass: "user-options" },
            [
              a(
                "transition",
                {
                  attrs: {
                    name: "custom-classes-transition",
                    "enter-active-class": "animated fadeIn",
                    "leave-active-class": "animated fadeOut",
                  },
                },
                [
                  a("div", {
                    directives: [
                      {
                        name: "show",
                        rawName: "v-show",
                        value: t.isOpen,
                        expression: "isOpen",
                      },
                    ],
                    staticClass: "shadow",
                    on: {
                      click: function (e) {
                        return t.open();
                      },
                    },
                  }),
                ],
              ),
              a(
                "transition",
                {
                  attrs: {
                    name: "custom-classes-transition",
                    "enter-active-class": "animated slideInUp",
                    "leave-active-class": "animated slideOutDown",
                    mode: "out-in",
                  },
                },
                [
                  a(
                    "div",
                    {
                      directives: [
                        {
                          name: "show",
                          rawName: "v-show",
                          value: t.isOpen,
                          expression: "isOpen",
                        },
                      ],
                      staticClass: "squart",
                    },
                    [
                      a("div", { staticClass: "container" }, [
                        a("div", { staticClass: "row" }, [
                          a("div", { staticClass: "col s12" }, [a("p")]),
                          a(
                            "form",
                            {
                              staticClass:
                                "col s12 m6 push-m3 login background-og",
                              on: {
                                submit: function (t) {
                                  t.preventDefault();
                                },
                              },
                            },
                            [
                              a("p", { staticClass: "derecha" }, [
                                t._v("\n\t\t\t\t\t\t\t\t "),
                                a(
                                  "a",
                                  {
                                    directives: [
                                      {
                                        name: "show",
                                        rawName: "v-show",
                                        value: !t.isLoading,
                                        expression: "!isLoading",
                                      },
                                    ],
                                    on: {
                                      click: function (e) {
                                        return t.open();
                                      },
                                    },
                                  },
                                  [t._v("X")],
                                ),
                              ]),
                              a("h3", { staticClass: "izquierda" }, [
                                t._v(t._s(t.$t("Ingresar"))),
                              ]),
                              a(
                                "p",
                                { staticClass: "izquierda" },
                                [
                                  t._v(
                                    "\n\t\t\t\t\t\t\t\t" +
                                      t._s(t.$t("maillbl")) +
                                      " ",
                                  ),
                                  a("font-awesome-icon", {
                                    directives: [
                                      {
                                        name: "show",
                                        rawName: "v-show",
                                        value: t.isLoading,
                                        expression: "isLoading",
                                      },
                                    ],
                                    attrs: { icon: "cog", spin: "" },
                                  }),
                                  a("span", { staticClass: "red-text" }, [
                                    t._v(t._s(t.error.name)),
                                  ]),
                                ],
                                1,
                              ),
                              a("input", {
                                directives: [
                                  {
                                    name: "model",
                                    rawName: "v-model.trim",
                                    value: t.user_t,
                                    expression: "user_t",
                                    modifiers: { trim: !0 },
                                  },
                                ],
                                class: { disabled: t.isLoading },
                                attrs: {
                                  type: "text",
                                  placeholder: t.$t("maillbl"),
                                  readonly: t.isLoading,
                                  id: "din_email",
                                  name: "din_email",
                                  autocomplete: "current-email",
                                },
                                domProps: { value: t.user_t },
                                on: {
                                  input: function (e) {
                                    e.target.composing ||
                                      (t.user_t = e.target.value.trim());
                                  },
                                  blur: function (e) {
                                    return t.$forceUpdate();
                                  },
                                },
                              }),
                              a(
                                "p",
                                { staticClass: "izquierda" },
                                [
                                  t._v(
                                    "\n\t\t\t\t\t\t\t\t" +
                                      t._s(t.$t("passwordlbl")) +
                                      " ",
                                  ),
                                  a("font-awesome-icon", {
                                    directives: [
                                      {
                                        name: "show",
                                        rawName: "v-show",
                                        value: t.isLoading,
                                        expression: "isLoading",
                                      },
                                    ],
                                    attrs: { icon: "cog", spin: "" },
                                  }),
                                  a("span", { staticClass: "red-text" }, [
                                    t._v(t._s(t.error.password)),
                                  ]),
                                ],
                                1,
                              ),
                              a("input", {
                                directives: [
                                  {
                                    name: "model",
                                    rawName: "v-model.trim",
                                    value: t.password,
                                    expression: "password",
                                    modifiers: { trim: !0 },
                                  },
                                ],
                                class: { disabled: t.isLoading },
                                attrs: {
                                  type: "password",
                                  placeholder: t.$t("passwordlbl"),
                                  readonly: t.isLoading,
                                  id: "din_password",
                                  name: "din_password",
                                  autocomplete: "current-password",
                                },
                                domProps: { value: t.password },
                                on: {
                                  input: function (e) {
                                    e.target.composing ||
                                      (t.password = e.target.value.trim());
                                  },
                                  blur: function (e) {
                                    return t.$forceUpdate();
                                  },
                                },
                              }),
                              a("p", { staticClass: "buttons derecha" }, [
                                a(
                                  "a",
                                  {
                                    staticClass: "send",
                                    class: { disabled: t.isLoading },
                                    on: {
                                      click: function (e) {
                                        return t.tryLogin();
                                      },
                                    },
                                  },
                                  [t._v(t._s(t.$t("txtSendLogin")))],
                                ),
                              ]),
                              a("p", { staticClass: "derecha" }, [
                                t._v(
                                  "\n\t\t\t\t\t\t\t\t" +
                                    t._s(t.$t("txtNoRegister")) +
                                    " ",
                                ),
                                a(
                                  "span",
                                  {
                                    on: {
                                      click: function (e) {
                                        return t.goto("/extend/user/register");
                                      },
                                    },
                                  },
                                  [t._v(t._s(t.$t("txtRegister")) + "!")],
                                ),
                              ]),
                            ],
                          ),
                        ]),
                      ]),
                    ],
                  ),
                ],
              ),
            ],
            1,
          );
        },
        d = [],
        h = (a("96cf"), a("3b8d")),
        p =
          (a("28a5"),
          function (t, e) {
            var a = new Date(),
              n = new Date(a.getTime() + 864e5),
              s = n.toUTCString();
            document.cookie = t + "=" + e + "; expires=" + s + "; path=/";
          });
      function f(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function m(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? f(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : f(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      var g = {
          name: "NavExtend",
          data: function () {
            return {
              modal: null,
              isOpen: !1,
              user_t: "",
              password: "",
              error: { name: "", password: "" },
            };
          },
          computed: m(
            {},
            Object(i["c"])([
              "base",
              "version",
              "api",
              "colors",
              "isLoading",
              "things",
              "user",
            ]),
          ),
          mixins: [o["a"]],
          methods: m({}, Object(i["b"])(["load", "setThings"]), {
            open: function () {
              this.isOpen = !this.isOpen;
            },
            tryLogin: function () {
              this.isLoading ||
                ((this.error.name = ""),
                (this.error.password = ""),
                "" == this.user_t &&
                  (this.error.name = this.$t("mandatoryField")),
                "" == this.password &&
                  (this.error.password = this.$t("mandatoryField")),
                "" != this.user_t && "" != this.password && this.getData());
            },
            getData: (function () {
              var t = Object(h["a"])(
                regeneratorRuntime.mark(function t() {
                  var e = this;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            if (!this.isLoading) {
                              t.next = 4;
                              break;
                            }
                            return t.abrupt("return", 0);
                          case 4:
                            this.load(!0);
                          case 5:
                            (this.setThings(this.user_t),
                              l()({
                                method: "POST",
                                url: this.api + "api/v2/users/login",
                                headers: m(
                                  {
                                    "Content-Type": "application/json",
                                    Accept: "application/json, text/plain, */*",
                                  },
                                  this.things,
                                ),
                                data: {
                                  user: this.user_t,
                                  password: this.password,
                                },
                              })
                                .then(function (t) {
                                  t.data.ok
                                    ? (localStorage.setItem(
                                        "tks",
                                        t.data.token,
                                      ),
                                      p("ts", t.data.token),
                                      localStorage.setItem(
                                        "user",
                                        JSON.stringify(t.data.user),
                                      ),
                                      e.goto("/extend"))
                                    : (1 == t.data.errorType &&
                                        (e.error.name = e.$t("mailDontExist")),
                                      2 == t.data.errorType &&
                                        (e.error.password =
                                          e.$t("wrongPassword")));
                                })
                                .catch(function (t) {
                                  M.toast({
                                    html: e.$t("informacionNoDisponible"),
                                  });
                                })
                                .finally(function () {
                                  e.load(!1);
                                }));
                          case 7:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                  );
                }),
              );
              function e() {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            tryOut: (function () {
              var t = Object(h["a"])(
                regeneratorRuntime.mark(function t() {
                  var e,
                    a = this;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            return (
                              localStorage.removeItem("tks"),
                              localStorage.removeItem("user"),
                              this.goto("/extend"),
                              this.load(!1),
                              t.abrupt("return", 0)
                            );
                          case 9:
                            this.load(!0);
                          case 10:
                            (this.setThings(),
                              (e = localStorage.getItem("tks")
                                ? localStorage.getItem("tks")
                                : ""),
                              l()({
                                method: "POST",
                                url: this.api + "check",
                                headers: m(
                                  {
                                    "Content-Type": "application/json",
                                    Accept: "application/json, text/plain, */*",
                                    t: "ua1001",
                                    t2: "logout",
                                    id: this.user.id,
                                    tkn: e,
                                  },
                                  this.things,
                                ),
                                data: { user: this.user.username },
                              })
                                .then(function (t) {
                                  t.data.ok ||
                                    M.toast({ html: t.data.message });
                                })
                                .catch(function (t) {
                                  M.toast({
                                    html: a.$t("informacionNoDisponible"),
                                  });
                                })
                                .finally(function () {
                                  (localStorage.removeItem("tks"),
                                    localStorage.removeItem("user"),
                                    (document.cookie =
                                      "ts=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"),
                                    a.goto("/extend"),
                                    a.load(!1));
                                }));
                          case 13:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                  );
                }),
              );
              function e() {
                return t.apply(this, arguments);
              }
              return e;
            })(),
          }),
          mounted: function () {},
        },
        v = g,
        b = (a("fb12"), a("2877")),
        w = Object(b["a"])(v, u, d, !1, null, "41c1fe2f", null),
        y = w.exports;
      function x(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function C(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? x(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : x(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      var _ = {
          name: "post",
          data: function () {
            return { posts: [], message: "", limit: 180, cargando: !1 };
          },
          components: { Login: y },
          props: {
            guia: { type: [Number, String], default: 0 },
            numero: { type: [Number, String], default: 0 },
            versionimp: { type: [Number, String], default: -1 },
          },
          mixins: [o["a"]],
          computed: C(
            {},
            Object(i["c"])([
              "base",
              "api",
              "things",
              "version",
              "user",
              "isLoading",
            ]),
            {
              count: function () {
                var t = this.limit - this.message.length;
                return t < 0 ? 0 : t;
              },
              v: function () {
                return -1 == this.versionimp
                  ? this.version.id
                  : this.versionimp;
              },
            },
          ),
          methods: C({}, Object(i["b"])(["setThings", "load"]), {
            makePost: function () {
              (this.posts.push({
                username: this.user.username,
                userpic: this.user.pic,
                comentario: this.message,
                estado: 0,
              }),
                this.trySaveCommnets(),
                (this.message = ""));
            },
            tryGetCommnets: function () {
              var t = this;
              (this.setThings(this.guia),
                l()({
                  method: "GET",
                  url:
                    this.api +
                    "api/v2/comment?v=" +
                    this.v +
                    "&g=" +
                    this.guia +
                    "&n=" +
                    this.numero +
                    "&v2=" +
                    this.version.id,
                  headers: C(
                    {
                      "Content-Type": "application/json",
                      Accept: "application/json, text/plain, */*",
                    },
                    this.things,
                  ),
                })
                  .then(function (e) {
                    e.data.ok && (t.posts = e.data.comentarios);
                  })
                  .catch(function (e) {
                    (t.check401(e),
                      M.toast({ html: t.$t("informacionNoDisponible") }));
                  })
                  .finally(function () {}));
            },
            trySaveCommnets: function () {
              var t = this;
              if (this.cargando) return 0;
              ((this.cargando = !0),
                this.setThings(this.guia),
                l()({
                  method: "POST",
                  url: this.api + "api/v2/comment?v=" + this.version.id,
                  data: {
                    comment: this.message,
                    guia: this.guia,
                    version: this.v,
                    numero: this.numero,
                  },
                  headers: C(
                    {
                      "Content-Type": "application/json",
                      Accept: "application/json, text/plain, */*",
                    },
                    this.things,
                  ),
                })
                  .then(function (t) {})
                  .catch(function (e) {
                    (t.check401(e),
                      M.toast({ html: t.$t("informacionNoDisponible") }));
                  })
                  .finally(function () {
                    t.cargando = !1;
                  }));
            },
            tryDeleteCommnets: function (t) {
              var e = this;
              if (this.cargando) return 0;
              ((this.cargando = !0),
                this.setThings(t.id),
                l()({
                  method: "DELETE",
                  url:
                    this.api +
                    "api/v2/comment/" +
                    t.id +
                    "?v=" +
                    this.version.id,
                  headers: C(
                    {
                      "Content-Type": "application/json",
                      Accept: "application/json, text/plain, */*",
                    },
                    this.things,
                  ),
                })
                  .then(function (a) {
                    a.data.ok && e.deleteElement(t);
                  })
                  .catch(function (t) {
                    (e.check401(t),
                      M.toast({ html: e.$t("informacionNoDisponible") }));
                  })
                  .finally(function () {
                    e.cargando = !1;
                  }));
            },
            deleteElement: function (t) {
              var e = [];
              (this.posts.forEach(function (a) {
                t != a && e.push(a);
              }),
                this.$set(this, "posts", e));
            },
            go: function (t) {
              window.open("/extend/user/profile?id=" + t, "_blank");
            },
          }),
          created: function () {
            this.tryGetCommnets();
          },
        },
        k = _,
        O = (a("20a4"), Object(b["a"])(k, n, s, !1, null, "da0c93c6", null));
      e["a"] = O.exports;
    },
    "0729": function (t, e, a) {
      "use strict";
      var n = a("38db"),
        s = a.n(n);
      s.a;
    },
    "0f2b": function (t, e, a) {},
    1082: function (t, e, a) {
      "use strict";
      var n = a("c75b"),
        s = a.n(n);
      s.a;
    },
    1107: function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a(
            "div",
            {
              directives: [
                {
                  name: "show",
                  rawName: "v-show",
                  value: t.isLoading && t.mostrar,
                  expression: "isLoading && mostrar",
                },
              ],
              staticClass: "flagwork",
            },
            [
              a(
                "h5",
                { staticClass: "red-text bordes-f" },
                [
                  a("font-awesome-icon", { attrs: { icon: "cog", spin: "" } }),
                  t._v(" " + t._s(t.text) + "\n    "),
                ],
                1,
              ),
            ],
          );
        },
        s = [],
        r = (a("8e6e"), a("ac6a"), a("456d"), a("bd86")),
        i = a("2f62");
      function o(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function c(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? o(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : o(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      var l = {
          name: "flagwork",
          props: {
            mostrar: { type: Boolean, default: !0 },
            text: { type: String, default: "" },
          },
          computed: c({}, Object(i["c"])(["isLoading"])),
          created: function () {},
        },
        u = l,
        d = (a("0729"), a("2877")),
        h = Object(d["a"])(u, n, s, !1, null, "22d2d271", null);
      e["a"] = h.exports;
    },
    "11af": function (t, e, a) {
      "use strict";
      var n = a("669c"),
        s = a.n(n);
      s.a;
    },
    "175e": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a(
            "div",
            {
              staticClass: "noti-wrapper",
              attrs: { "aria-live": "polite", "aria-atomic": "false" },
            },
            [
              a(
                "transition-group",
                {
                  staticClass: "noti-stack",
                  attrs: { name: "noti-list", tag: "div" },
                },
                t._l(t.notificationsCopy, function (e) {
                  return a(
                    "div",
                    {
                      key: e.id,
                      class: ["noti-toast", "noti-" + e.type],
                      attrs: { role: "alert" },
                    },
                    [
                      a("div", { staticClass: "noti-icon-wrap" }, [
                        a(
                          "svg",
                          {
                            staticClass: "noti-icon",
                            attrs: {
                              viewBox: "0 0 24 24",
                              fill: "none",
                              xmlns: "http://www.w3.org/2000/svg",
                            },
                          },
                          [
                            "success" === e.type
                              ? a("path", {
                                  attrs: {
                                    d: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
                                    stroke: "currentColor",
                                    "stroke-width": "2",
                                    "stroke-linecap": "round",
                                    "stroke-linejoin": "round",
                                  },
                                })
                              : "info" === e.type
                                ? a("path", {
                                    attrs: {
                                      d: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
                                      stroke: "currentColor",
                                      "stroke-width": "2",
                                      "stroke-linecap": "round",
                                      "stroke-linejoin": "round",
                                    },
                                  })
                                : "warning" === e.type
                                  ? a("path", {
                                      attrs: {
                                        d: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
                                        stroke: "currentColor",
                                        "stroke-width": "2",
                                        "stroke-linecap": "round",
                                        "stroke-linejoin": "round",
                                      },
                                    })
                                  : "danger" === e.type
                                    ? a("path", {
                                        attrs: {
                                          d: "M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z",
                                          stroke: "currentColor",
                                          "stroke-width": "2",
                                          "stroke-linecap": "round",
                                          "stroke-linejoin": "round",
                                        },
                                      })
                                    : t._e(),
                          ],
                        ),
                      ]),
                      a("div", { staticClass: "noti-body" }, [
                        e.title
                          ? a("p", { staticClass: "noti-title" }, [
                              t._v(t._s(e.title)),
                            ])
                          : t._e(),
                        e.message
                          ? a("p", { staticClass: "noti-message" }, [
                              t._v(t._s(e.message)),
                            ])
                          : t._e(),
                      ]),
                      a(
                        "button",
                        {
                          staticClass: "noti-close",
                          attrs: { "aria-label": "Cerrar" },
                          on: {
                            click: function (a) {
                              return t.remove(e.id);
                            },
                          },
                        },
                        [
                          a(
                            "svg",
                            {
                              attrs: {
                                viewBox: "0 0 24 24",
                                fill: "none",
                                xmlns: "http://www.w3.org/2000/svg",
                              },
                            },
                            [
                              a("path", {
                                attrs: {
                                  d: "M6 18L18 6M6 6l12 12",
                                  stroke: "currentColor",
                                  "stroke-width": "2",
                                  "stroke-linecap": "round",
                                  "stroke-linejoin": "round",
                                },
                              }),
                            ],
                          ),
                        ],
                      ),
                      a("div", {
                        staticClass: "noti-progress-bar",
                        style: { animationDuration: e.duration + "ms" },
                      }),
                    ],
                  );
                }),
                0,
              ),
            ],
            1,
          );
        },
        s = [],
        r = (a("8e6e"), a("456d"), a("75fc")),
        i = (a("ac6a"), a("bd86")),
        o = a("2f62");
      function c(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function l(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? c(a, !0).forEach(function (e) {
                Object(i["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : c(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      var u = {
          name: "NotificationToast",
          data: function () {
            return { notificationsCopy: [] };
          },
          computed: l({}, Object(o["c"])(["notifications"])),
          watch: {
            notifications: {
              deep: !0,
              handler: function (t, e) {
                var a = this;
                (t.forEach(function (t) {
                  var e =
                    a.notificationsCopy &&
                    a.notificationsCopy.some(function (e) {
                      return e.id === t.id;
                    });
                  e || a.scheduleRemove(t);
                }),
                  this.$set(this, "notificationsCopy", Object(r["a"])(t)));
              },
            },
          },
          methods: l({}, Object(o["b"])(["removeNotification"]), {
            remove: function (t) {
              this.removeNotification(t);
            },
            scheduleRemove: function (t) {
              var e = this;
              t.duration > 0 &&
                setTimeout(function () {
                  e.removeNotification(t.id);
                }, t.duration);
            },
          }),
        },
        d = u,
        h = (a("4b1a"), a("2877")),
        p = Object(h["a"])(d, n, s, !1, null, "1754a124", null);
      e["a"] = p.exports;
    },
    "1d4b": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", { staticClass: "face-foe" }, [
            a("div", { staticClass: "row", style: t.fix.style }, [
              a("div", { staticClass: "col s12 centrado" }, [
                a("div", { staticClass: "img-can" }, [
                  a("canvas", {
                    class: [
                      this.fix.sh ? "sh" : "",
                      this.fix.color,
                      this.fix.emit_pixel ? "manito" : "",
                    ],
                    attrs: {
                      width: t.fix.width,
                      height: t.fix.height,
                      id: "can" + t.id,
                    },
                    on: {
                      click: function (e) {
                        return t.getPixel(e);
                      },
                    },
                  }),
                ]),
              ]),
            ]),
          ]);
        },
        s = [],
        r = (a("8e6e"), a("456d"), a("ac6a"), a("bd86"));
      a("c5f6");
      function i(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function o(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? i(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : i(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      var c = {
          name: "ImagePatched",
          data: function () {
            return { header: [], body: [], data: [] };
          },
          props: {
            batch: {
              type: DataView,
              default: function () {
                return {};
              },
            },
            id: {
              type: [String, Number],
              default: function () {
                return Date.now();
              },
            },
            config: {
              type: Object,
              default: function () {
                return {};
              },
            },
            chunks: {
              type: Array,
              default: function () {
                return [
                  {
                    width: 128,
                    height: 160,
                    data: { ci: { x: 0, y: 0 }, cf: { x: 160, y: 128 } },
                    canvas: { ci: { x: 0, y: 0 }, cf: { x: 128, y: 160 } },
                  },
                ];
              },
            },
          },
          computed: {
            fix: function () {
              return o(
                {
                  width: 320,
                  height: 160,
                  num_colors: 256,
                  bytes_width: 128,
                  bytes_height: 160,
                  body_offset: parseInt("10FB000", 16),
                  pallete_offset: 17870848,
                  ppb: 1,
                  sh: !0,
                  emitb64: !1,
                  color: "no",
                  emit_pixel: !1,
                  clear_before_render: !1,
                  avoidTransparent: !1,
                  style: {},
                },
                this.config,
              );
            },
          },
          methods: {
            paintCanvas: function () {
              var t = this,
                e = document.querySelector("#can" + this.id),
                a = e.getContext("2d"),
                n = a.createImageData(e.width, e.height);
              ((this.data = n.data),
                this.clear(),
                this.chunks.forEach(function (a) {
                  for (var n = 0; n < (a.width * a.height) / t.fix.ppb; n++) {
                    var s = t.batch.getUint8(
                      t.fix.body_offset +
                        t.fix.bytes_width * a.data.ci.y +
                        t.fix.bytes_width *
                          parseInt(n / (a.width / t.fix.ppb)) +
                        (n % (a.width / t.fix.ppb)) +
                        a.data.ci.x,
                      !0,
                    );
                    if (1 == t.fix.ppb) {
                      var r = t.header[0];
                      (s < t.fix.num_colors && (r = t.header[s]),
                        t.drawPixel(r, e, a, n));
                    }
                    if (2 == t.fix.ppb) {
                      var i = 15 & s,
                        o = s >> 4,
                        c = t.header[0];
                      (i < t.fix.num_colors && (c = t.header[i]),
                        t.drawPixel(c, e, a, 2 * n),
                        (c = t.header[0]),
                        o < t.fix.num_colors && (c = t.header[o]),
                        t.drawPixel(c, e, a, 2 * n + 1));
                    }
                  }
                }),
                this.swapBuffer(a, n),
                this.exportB64());
            },
            drawPixel: function (t, e, a, n) {
              var s = Math.round(
                  a.width * (a.mirror ? 1 : 0) +
                    (a.mirror ? -1 : 1) * (n % a.width) +
                    a.canvas.ci.x,
                ),
                r = Math.round(parseInt(n / a.width) + a.canvas.ci.y),
                i = 4 * (e.width * r + s);
              (!this.fix.avoidTransparent ||
                (this.fix.avoidTransparent && 0 != t.a)) &&
                ((this.data[i + 0] = t.r),
                (this.data[i + 1] = t.g),
                (this.data[i + 2] = t.b),
                (this.data[i + 3] = t.a));
            },
            swapBuffer: function (t, e) {
              t.putImageData(e, 0, 0);
            },
            getHeader: function () {
              var t = this,
                e = this.fix.pallete_offset,
                a = [];
              if (null != this.batch) {
                for (var n = 0; n < this.fix.num_colors; n += 1) {
                  var s = this.batch.getUint8(2 * n + e, !0),
                    r = this.batch.getUint8(2 * n + 1 + e, !0),
                    i = (s & parseInt("1F", 16)) << 3,
                    o =
                      ((r & parseInt("3", 16)) << 6) |
                      ((s & parseInt("E0", 16)) >> 2),
                    c = (r & parseInt("7C", 16)) << 1,
                    l = r & parseInt("80", 16);
                  a.push({
                    r: i,
                    g: o,
                    b: c,
                    a: 0 == l && 0 == c && 0 == o && 0 == i ? 0 : 255,
                  });
                }
                (this.$set(this, "header", a),
                  setTimeout(function () {
                    t.paintCanvas();
                  }, 0));
              }
            },
            draw: function () {
              this.getHeader();
            },
            exportB64: function () {
              if (!this.fix.emitb64) return 0;
              var t = document.getElementById("can" + this.id),
                e = "" + t.toDataURL();
              this.$emit("update:image", e);
            },
            findPos: function (t) {
              var e = 0,
                a = 0;
              if (t.offsetParent) {
                do {
                  ((e += t.offsetLeft), (a += t.offsetTop));
                } while ((t = t.offsetParent));
                return { x: e, y: a };
              }
            },
            getPixel: function (t) {
              if (!this.fix.emit_pixel) return 0;
              var e = document.getElementById("can" + this.id),
                a = this.findPos(e),
                n = parseInt(
                  ((t.pageX - a.x) * this.fix.width) / e.offsetWidth,
                ),
                s = parseInt(
                  ((t.pageY - a.y) * this.fix.height) / e.offsetHeight,
                ),
                r = e.getContext("2d"),
                i = r.getImageData(n, s, 1, 1).data;
              this.$emit("emit:pixel", { r: i[0], g: i[1], b: i[2], a: i[3] });
            },
            clear: function () {
              if (!this.fix.clear_before_render) return 0;
              for (var t = 0; t < this.fix.width; t++)
                for (var e = 0; e < this.fix.height; e++)
                  ((this.data[4 * (t + this.fix.width * e) + 0] = 0),
                    (this.data[4 * (t + this.fix.width * e) + 1] = 0),
                    (this.data[4 * (t + this.fix.width * e) + 2] = 0),
                    (this.data[4 * (t + this.fix.width * e) + 3] = 0));
            },
          },
          watch: {
            batch: function (t, e) {
              this.batch && this.draw();
            },
          },
          mounted: function () {
            var t = this;
            this.$nextTick(function () {
              t.draw();
            });
          },
        },
        l = c,
        u = (a("ef35"), a("2877")),
        d = Object(u["a"])(l, n, s, !1, null, "3e8e78e4", null);
      e["a"] = d.exports;
    },
    "20a4": function (t, e, a) {
      "use strict";
      var n = a("757c"),
        s = a.n(n);
      s.a;
    },
    "243e": function (t, e, a) {},
    "24d8": function (t, e, a) {
      "use strict";
      var n = a("0f2b"),
        s = a.n(n);
      s.a;
    },
    2814: function (t, e, a) {
      var n = {
        "./en.json": ["3673"],
        "./es.json": ["c3d7"],
        "./fr.json": ["b16d", "chunk-2d20ec33"],
        "./pt.json": ["4ea9", "chunk-2d0ccb5f"],
        "./vn.json": ["2ec1", "chunk-2d0be2d7"],
      };
      function s(t) {
        var e = n[t];
        return e
          ? Promise.all(e.slice(1).map(a.e)).then(function () {
              var t = e[0];
              return a.t(t, 3);
            })
          : Promise.resolve().then(function () {
              var e = new Error("Cannot find module '" + t + "'");
              throw ((e.code = "MODULE_NOT_FOUND"), e);
            });
      }
      ((s.keys = function () {
        return Object.keys(n);
      }),
        (s.id = "2814"),
        (t.exports = s));
    },
    "287d": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", { staticClass: "face-foe" }, [
            a("div", { staticClass: "row" }, [
              t.isLoading
                ? a("div", { staticClass: "col s12 centrado" }, [
                    a("h5", { staticClass: "germania white-text sh-t-2" }, [
                      t._v(t._s(t.$t("loading")) + "..."),
                    ]),
                  ])
                : t._e(),
              a(
                "div",
                {
                  directives: [
                    {
                      name: "show",
                      rawName: "v-show",
                      value: t.fix.show,
                      expression: "fix.show",
                    },
                  ],
                  staticClass: "col s12 centrado",
                },
                [
                  a("div", { staticClass: "img-can" }, [
                    a("canvas", {
                      class: [
                        this.fix.sh ? "sh" : "",
                        this.fix.color,
                        this.fix.emit_pixel ? "manito" : "",
                      ],
                      attrs: {
                        width: t.fix.width,
                        height: t.fix.height,
                        id: "can" + t.id,
                      },
                    }),
                  ]),
                ],
              ),
            ]),
          ]);
        },
        s = [],
        r = (a("8e6e"), a("456d"), a("55dd"), a("ac6a"), a("8615"), a("bd86"));
      a("c5f6");
      function i(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function o(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? i(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : i(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      var c = {
          name: "ImageConverter",
          data: function () {
            return {
              header: [],
              body: [],
              data: [],
              histogram: [],
              isLoading: !1,
            };
          },
          props: {
            batch: {
              type: DataView,
              default: function () {
                return null;
              },
            },
            id: {
              type: [String, Number],
              default: function () {
                return Date.now();
              },
            },
            config: {
              type: Object,
              default: function () {
                return {};
              },
            },
          },
          computed: {
            fix: function () {
              return o(
                {
                  width: 320,
                  height: 160,
                  num_colors: 256,
                  bytes_width: 128,
                  bytes_height: 160,
                  sh: !0,
                  clear_before_render: !1,
                  keep_black: !1,
                  show: !1,
                },
                this.config,
              );
            },
          },
          methods: {
            paintCanvas: function () {
              var t = this,
                e = document.querySelector("#can" + this.id),
                a = e.getContext("2d"),
                n = a.createImageData(e.width, e.height);
              if (((this.data = n.data), this.clear(), this.batch)) {
                (this.$set(this, "isLoading", !0),
                  this.$emit("editing:image", !0));
                var s = new Image();
                ((s.onload = function () {
                  (a.drawImage(s, 0, 0),
                    t.createHeader(),
                    t.createBody(),
                    t.$emit("update:image", { header: t.header, body: t.body }),
                    t.$set(t, "isLoading", !1),
                    t.$emit("editing:image", !1));
                }),
                  (s.src = window.URL.createObjectURL(
                    new Blob([this.batch.buffer], {
                      type: "application/octet-stream",
                    }),
                  )),
                  this.swapBuffer(a, n));
              }
            },
            swapBuffer: function (t, e) {
              t.putImageData(e, 0, 0);
            },
            clear: function () {
              if (!this.fix.clear_before_render) return 0;
              for (var t = 0; t < this.fix.width; t++)
                for (var e = 0; e < this.fix.height; e++)
                  ((this.data[4 * (t + this.fix.width * e) + 0] = 0),
                    (this.data[4 * (t + this.fix.width * e) + 1] = 0),
                    (this.data[4 * (t + this.fix.width * e) + 2] = 0),
                    (this.data[4 * (t + this.fix.width * e) + 3] = 0));
            },
            createHeader: function () {
              var t = {},
                e = document.getElementById("can" + this.id),
                a = e.getContext("2d");
              if (this.batch)
                for (var n = 0; n < this.fix.height; n++)
                  for (var s = 0; s < this.fix.width; s++) {
                    var r = a.getImageData(s, n, 1, 1).data,
                      i = 8 * parseInt(r[0] / 8),
                      o = 8 * parseInt(r[1] / 8),
                      c = 8 * parseInt(r[2] / 8),
                      l = 0 == r[3] ? 0 : 255;
                    (i + o + c == 0 &&
                      this.fix.keep_black &&
                      255 == l &&
                      ((i = 8), (o = 8), (c = 8), (l = 255)),
                      t["r" + i + "g" + o + "b" + c]
                        ? t["r" + i + "g" + o + "b" + c].r++
                        : (t["r" + i + "g" + o + "b" + c] = {
                            header: { r: i, g: o, b: c, a: l },
                            r: 1,
                            order: 65536 * i + 256 * o + c,
                          }));
                  }
              ((t = Object.values(t)),
                t.sort(function (t, e) {
                  return e.r - t.r;
                }));
              for (var u = [], d = 0; d < this.fix.num_colors; d++)
                t[d] ? u.push(t[d]) : u.push(t[0]);
              (u.sort(function (t, e) {
                return t.order - e.order;
              }),
                this.$set(this, "histogram", u));
              var h = [];
              (this.histogram.forEach(function (t) {
                h.push(t.header);
              }),
                this.$set(this, "header", h));
            },
            createBody: function () {
              var t = [],
                e = document.getElementById("can" + this.id),
                a = e.getContext("2d");
              if ((this.$set(this, "body", t), this.batch))
                for (var n = "", s = 0, r = 0; r < this.fix.height; r++)
                  for (var i = 0; i < this.fix.width; i++) {
                    var o = a.getImageData(i, r, 1, 1).data,
                      c = 16777216,
                      l = 8 * parseInt(o[0] / 8),
                      u = 8 * parseInt(o[1] / 8),
                      d = 8 * parseInt(o[2] / 8),
                      h = 0 == o[3] ? 0 : 255;
                    if (n == "r" + l + "g" + u + "b" + d + "a" + h) t.push(s);
                    else {
                      if (((n = "r" + l + "g" + u + "b" + d + "a" + h), 0 == h))
                        for (var p = 0; p < this.fix.num_colors; p++)
                          0 == this.histogram[p].header.a &&
                            ((s = p), (p = this.fix.num_colors));
                      else
                        for (var f = 0; f < this.fix.num_colors; f++) {
                          var m = Math.sqrt(
                            Math.pow(l - this.histogram[f].header.r, 2) +
                              Math.pow(u - this.histogram[f].header.g, 2) +
                              Math.pow(d - this.histogram[f].header.b, 2),
                          );
                          (m <= c &&
                            0 != this.histogram[f].header.a &&
                            ((c = m), (s = f)),
                            0 == c && (f = this.fix.num_colors));
                        }
                      t.push(s);
                    }
                  }
              this.$set(this, "body", t);
            },
          },
          watch: {
            batch: function (t, e) {
              this.paintCanvas();
            },
          },
          mounted: function () {
            var t = this;
            this.$nextTick(function () {
              t.paintCanvas();
            });
          },
        },
        l = c,
        u = (a("d32e"), a("2877")),
        d = Object(u["a"])(l, n, s, !1, null, "2f41a218", null);
      e["a"] = d.exports;
    },
    "2e8f": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", { staticClass: "tool-editor" }, [
            a("div", [t._t("left")], 2),
            a("div", [t._t("right")], 2),
          ]);
        },
        s = [],
        r = { name: "ToolEditorLayout" },
        i = r,
        o = (a("572b"), a("2877")),
        c = Object(o["a"])(i, n, s, !1, null, "f34d5ef6", null);
      e["a"] = c.exports;
    },
    "2f80": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a(
            "div",
            { staticClass: "cookie" },
            [
              a(
                "transition",
                {
                  attrs: {
                    name: "custom-classes-transition",
                    "enter-active-class": "animated fadeIn",
                    "leave-active-class": "animated fadeOut",
                  },
                },
                [
                  a("div", {
                    directives: [
                      {
                        name: "show",
                        rawName: "v-show",
                        value: !t.isLoading && !t.isReady,
                        expression: "!isLoading && !isReady",
                      },
                    ],
                  }),
                ],
              ),
              a(
                "transition",
                {
                  attrs: {
                    name: "custom-classes-transition",
                    "enter-active-class": "animated slideInUp",
                    "leave-active-class": "animated slideOutDown",
                    mode: "out-in",
                  },
                },
                [
                  a(
                    "div",
                    {
                      directives: [
                        {
                          name: "show",
                          rawName: "v-show",
                          value: !t.isLoading && !t.isReady,
                          expression: "!isLoading && !isReady",
                        },
                      ],
                      staticClass: "cookie-body",
                    },
                    [
                      a("p", { staticClass: "justificado" }, [
                        t._v(
                          "\n            " +
                            t._s(t.$t("cockieMessage")) +
                            "\n        ",
                        ),
                      ]),
                      a("div", { staticClass: "derecha" }, [
                        a(
                          "a",
                          {
                            staticClass:
                              "btn-flat waves-effect waves-green  amber-text",
                            on: {
                              click: function (e) {
                                return t.save(!0);
                              },
                            },
                          },
                          [t._v(t._s(t.$t("agree")))],
                        ),
                        a(
                          "a",
                          {
                            staticClass:
                              "btn-flat waves-effect waves-red amber-text",
                            on: {
                              click: function (e) {
                                return t.save(!1);
                              },
                            },
                          },
                          [t._v(t._s(t.$t("later")))],
                        ),
                      ]),
                    ],
                  ),
                ],
              ),
              t.releaseMessage ? a("PopMessage", { ref: "message" }) : t._e(),
            ],
            1,
          );
        },
        s = [],
        r = (a("8e6e"), a("ac6a"), a("456d"), a("bd86")),
        i = a("2f62"),
        o = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", { staticClass: "message-panel" }, [
            a(
              "div",
              [
                a(
                  "transition",
                  {
                    attrs: {
                      name: "custom-classes-transition",
                      "enter-active-class": "animated slideInDown",
                      "leave-active-class": "animated slideOutUp",
                      mode: "out-in",
                    },
                  },
                  [
                    a(
                      "div",
                      {
                        directives: [
                          {
                            name: "show",
                            rawName: "v-show",
                            value: t.visible,
                            expression: "visible",
                          },
                        ],
                        staticClass: "roboto bg-fiber",
                      },
                      [
                        a(
                          "div",
                          [
                            a(
                              "span",
                              {
                                staticClass: "x roboto",
                                on: {
                                  click: function (e) {
                                    return t.close();
                                  },
                                },
                              },
                              [t._v("X")],
                            ),
                            a("br"),
                            t._l(t.pops, function (e) {
                              return a("div", { key: "not-" + e.id }, [
                                "-" != e.html || t.showDummy
                                  ? t._e()
                                  : a(
                                      "div",
                                      { staticClass: "izquierda normal" },
                                      [
                                        a("h5", [t._v(t._s(e.titulo))]),
                                        a("p", { staticClass: "roboto" }, [
                                          t._v(t._s(e.cuerpo)),
                                        ]),
                                      ],
                                    ),
                                "-" == e.html || t.showDummy
                                  ? t._e()
                                  : a("div", {
                                      domProps: { innerHTML: t._s(e.html) },
                                    }),
                                t.showDummy
                                  ? a("div", {
                                      domProps: { innerHTML: t._s(t.dummy) },
                                    })
                                  : t._e(),
                              ]);
                            }),
                          ],
                          2,
                        ),
                      ],
                    ),
                  ],
                ),
              ],
              1,
            ),
          ]);
        },
        c = [],
        l = a("bc3a"),
        u = a.n(l);
      function d(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function h(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? d(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : d(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      var p = {
          name: "Messages",
          data: function () {
            return {
              visible: !1,
              pops: [],
              popkeys: [],
              showDummy: !1,
              dummy: "",
            };
          },
          computed: h({}, Object(i["c"])(["api", "things", "version"])),
          methods: h({}, Object(i["b"])(["setThings"]), {
            close: function () {
              (this.$set(this, "visible", !1),
                localStorage.setItem("popkeys", JSON.stringify(this.popkeys)));
            },
            setKeys: function (t) {
              var e = this;
              ((this.popkeys = []),
                t.forEach(function (t) {
                  e.popkeys.push(t.id);
                }));
            },
            checkKeys: function (t) {
              var e = this,
                a = [];
              (t.forEach(function (t) {
                -1 == e.popkeys.indexOf(t.id) && a.push(t);
              }),
                this.$set(this, "pops", a));
            },
            getData: function () {
              var t = this;
              (this.setThings(),
                u()({
                  method: "GET",
                  url: this.api + "api/v2/pops?v=" + this.version.id,
                  headers: h(
                    {
                      "Content-Type": "application/json",
                      Accept: "application/json, text/plain, */*",
                    },
                    this.things,
                  ),
                }).then(function (e) {
                  e.data.ok &&
                    (t.checkKeys(e.data.pops),
                    t.setKeys(e.data.pops),
                    t.pops.length && t.$set(t, "visible", !0));
                }));
            },
          }),
          mounted: function () {
            var t = this;
            this.$nextTick(function () {
              t.getData();
            });
          },
          created: function () {
            localStorage.getItem("popkeys") &&
              (this.popkeys = JSON.parse(localStorage.getItem("popkeys")));
          },
        },
        f = p,
        m = (a("4ec0"), a("2877")),
        g = Object(m["a"])(f, o, c, !1, null, "296db70e", null),
        v = g.exports;
      function b(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function w(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? b(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : b(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      var y = {
          name: "Cookies",
          data: function () {
            return { isReady: !1, releaseMessage: !1 };
          },
          components: { PopMessage: v },
          computed: w({}, Object(i["c"])(["isLoading"])),
          methods: {
            save: function (t) {
              (t
                ? localStorage.setItem("isCookieAcepted", !0)
                : sessionStorage.setItem("isCookieAcepted", !0),
                (this.isReady = !0),
                (document.getElementsByTagName("body")[0].style.overflowY =
                  "auto"),
                (this.releaseMessage = !0));
            },
          },
          mounted: function () {
            this.isReady
              ? (this.releaseMessage = !0)
              : (document.getElementsByTagName("body")[0].style.overflowY =
                  "hidden");
          },
          created: function () {
            localStorage.getItem("isCookieAcepted")
              ? (this.isReady = JSON.parse(
                  localStorage.getItem("isCookieAcepted"),
                ))
              : sessionStorage.getItem("isCookieAcepted") &&
                (this.isReady = JSON.parse(
                  sessionStorage.getItem("isCookieAcepted"),
                ));
          },
        },
        x = y,
        C = (a("b64e"), Object(m["a"])(x, n, s, !1, null, "2c960101", null));
      e["a"] = C.exports;
    },
    "31c3": function (t, e, a) {},
    "33ef": function (t, e, a) {},
    3673: function (t) {
      t.exports = {
        advaceDownloaded: "Progress downloaded!",
        advaceUpdated: "Progress Updated",
        agree: "I agree",
        agregado: "aggregate!",
        alreadyMailExist: "The mail is already in use!",
        alreadyUserExist: "The username already exist!",
        anuncios: "Announcements",
        articulos: "Articles",
        ataque: "Attack",
        avatar: "Avatar",
        backups: "Backups",
        baseDeDatos: "Yugioh! Forbidden Memories and mods Database",
        basicData: "Basic Data",
        bestCards: "Best Week's card",
        blockCompatibility: "This block is compatible with all those versions",
        boughts: "Boughts",
        buscar: "Search",
        buscarCarta: "Search a card",
        campoLLeno: "The field is full!",
        cardsOnChest: "Cards on chest",
        carta: "Card",
        cartas: "cards",
        Cartas: "Cards",
        change: "Change",
        chestRequirements: "Chest Requirements",
        choiseAnotherMemory:
          "Choise another file, this memory don't has FM Save",
        choiseBlock: "Choise a Memorycard Block",
        choiseYourMemory: "Choise your memorycard",
        chooseAvatar: "Choose an Avatar",
        clasico: "Classic",
        cockieMessage:
          "This site uses its own and third party cookies in order to give you a personalized experience, continuing to use the site implies your acceptance.",
        confirmAvatar: "Confirm your Avatar",
        consultar: "Consult",
        corruptedData: "Corrupted Data!",
        createBackup: "Create Backup",
        createUserMsg: "User created!",
        data: "Data",
        deck: "Deck",
        deckDe: "Deck of",
        deckInicial: "initial deck",
        defensa: "Defending",
        deIn: "Initial Deck",
        deleteAdvance: "Delete Progress",
        deleteAdvanceBody:
          "This action will erase your data in your account, all your progress will be erased",
        deleteBackup: "Delete Backup",
        deleteBackupBody:
          "This action will erase your backup from your account, and can not be recovered",
        deleteGame: "Delete Game",
        deleteGameBody:
          "This action will erase your game from the last decks, and can not be recovered",
        deleteLocalData: "Delete local data",
        deleteLocalDataBody:
          "This action will erase your local data in this device, all your cards will be unmark.",
        descripcionClasico: "Classic Mode, now enhanced to support more mods!",
        descripcionExtendido:
          "Extended version, with more features and data, so you can also create an account to access even more features",
        descripcionGuia: "Cards, opponents, equips and more",
        descripcionHerramientas: "Utility",
        descripcionIngresar: "Access your account",
        descripcionNoticias: "Announcements, statistics and more",
        dowladAdvance: "Download Progress",
        dowladAdvanceBody:
          "This action will replace your local data in this device, all your cards will be replace for the data on your account",
        dropRate: "Drop Rate",
        edit: "Edit",
        editData: "Edit your Data",
        ejemplos: "Examples",
        elige: "Choose a version of Tea-Online",
        emptyBackups: "This user hasn´t public Backups to Show",
        emptyGames: "This user hasn´t games to Show",
        equipCards: "Equips Cards",
        equipos: "equips",
        Equipos: "Equips",
        equiposCompatibles: "Compatible equipment",
        erasedLoacalData: "Local data erased",
        estrella: "Star",
        extendido: "Extended",
        fusion: "Fusion",
        fusionar: "Fuse",
        fusiones: "fusions",
        fusiones1: "Fusions",
        fusiones2: "Fusions with this card",
        fusionesM: "Fusions",
        games: "Games",
        guiaCartas: "Card Guide",
        guiaDeckInicial: "Initial Deck Guide",
        guiaEquipos: "Equipment Guide",
        guiaFusiones: "Fusion Guide",
        guiaOponentes: "Opponents Guide",
        guiaRituales: "Ritual Guide",
        guias: "Guides",
        hasAccount: "Do you have account",
        Herramientas: "Tools",
        hideMemory: "Hide Memorycard",
        hideMemoryBody:
          "This action will hide your Memorycard, nobody will can donload it",
        informacionNoDisponible: "The information is not available",
        ingresaNombre: "Enter the name or number of a card",
        Ingresar: "Login",
        lastname: "Lastname",
        later: "Maybe later",
        latestSaves: "Latest User´s saves",
        lectorMemoria: "Memorycard reader",
        listaAnunciosNoDisponible: "The list of ads is not available",
        listaCartasNoDisponible: "The list of cards is not available",
        listaEquiposNoDisponibles: "The Equipment list is not available",
        listaNoticiasNoDisponible: "The News list is not available",
        listaOponentesNoDisponible: "The list of Opponents is not available",
        listaVersionesNoDisponible: "The version list is not available",
        loading: "Now Loading",
        localData: "Local Data",
        localMemoryEmpy: "Local Memory is Empty",
        logout: "Logout",
        Mail: "Mail",
        mailDontExist: "The mail is not registered!",
        maillbl: "email",
        makeFusion: "Make a Fusion",
        makePublic: "Make Public",
        makePublicBody:
          "This action will make public your Memorycard, everybody will can donload it",
        mandatoryField: "Mandatory Field",
        manoLLena: "The hand is full!",
        marked: "Show marked cards",
        memory: "Memory",
        memorycardReader: "Memorycard Reader",
        mensajeContacto:
          "Do you have a mod that should be in TeaOnline? Send an email to: ",
        newAvatarMsg: "New Avatar selected!",
        newPassword: "New Password",
        newPasswordx2: "Repeat your new Password",
        next: "Next",
        no: "No",
        noAdvances: "There is not Progress on your account",
        noBackups: "You dont have Backups!",
        noGames: "There is not Games saved!",
        nombre: "Name",
        Noticias: "News",
        numero: "Number",
        numRows: "Num Rows",
        obtained: "Obtained",
        oldPassword: "Old Password",
        onLibrary: "On Library",
        oponente: "Opponent",
        oponentes: "opponents",
        Oponentes: "Opponents",
        oponentesDan: "Opponents who gives this card",
        oponentesUsan: "Opponents using this card",
        opponentDeckRate: "Opponent's Deck rate",
        options: "Options",
        page: "Page",
        password: "Password",
        passwordlbl: "password",
        Passwords: "Passwords",
        picture: "Picture",
        precio: "Price",
        previus: "Previus",
        probabilidad: "Probability",
        profile: "Profile",
        pulsaBoton: "Press the button to access the guide",
        rango: "Rank",
        rankCalculator: "Rank Calculator",
        ranker: "Rank Calculator",
        rankMsg:
          "Each action in a duel change your duel points, when the duel is over you will be clasificate with a rank according with your points. This tool will calculate the current rank according your actions.",
        register: "Register",
        repeatPassword: "Repeat your password",
        resultado: "Result",
        ritualCards: "Ritual Cards",
        rituales: "rituals",
        Rituales: "Rituals",
        rituales2: "Rituals with this card",
        saveData: "Save Data",
        searchYourMemory: "Search your Memorycard",
        seleccionaEquipo: "Select a equip",
        seleccionaOponente: "Select an opponent",
        selectYourData: "Select your save data",
        shareMsg: "Share your progress! Make a BackUp and Keep your Game!",
        showOnlyType: "Show only type",
        si: "Yes",
        simulate: "Simulate",
        simulatorInitial: "Simulator of Initial Deck",
        sinResultados: "No results",
        specialConditions: "Special Conditions",
        SupportKeepGoing: "Support #TEAONLINE to keep going!",
        supportThrough: "Support us through",
        sure: "Are you sure?",
        syncGame: "Sync Game with local data",
        syncGameBody:
          "This action will replace your progress on this device, but dont update the copy on your account. If you wish update your copy on your account go to the Local Data Section.",
        tapClick: "Tap or Click on the fusion result to place on field",
        tea: "Everything is here!",
        text: "Text",
        textoDeckInicial:
          "The initial Deck is made up of a certain number of cards from 7 groups. In total the deck is made up of 40 cards.",
        textoPanelFusion: "Fusions simulator for cards on hand and field.",
        textoPanelInicial: "Set of cards for creating the initial deck.",
        textoPanelPassword: "Card codes to buy with starchips.",
        textoPanelRitual: "Requirements for ritual invocation of cards.",
        textoPanelTorre:
          "Drop from the last duel of the special game mode, present in some mods.",
        tipo: "Type",
        top10: "Top 10 - Cards",
        torre: "Tower",
        txtNoRegister: "You don´t register yet?",
        txtRegister: "Register",
        txtSendLogin: "Send",
        ultimaActualizacion: "Updated",
        ultimosDecks: "Latest Decks",
        uniqueCards: "Uniques Cards",
        updatePassword: "Update Password",
        updateProfile: "Update Profile",
        uploadAdvance: "Upload Progress",
        uploadAdvanceBody:
          "This action will replace your data on your account, all your cards will be replace for the data from this device and can not recovered",
        username: "User",
        usernameLabel: "Username",
        validMailMsg: "Input a valid email",
        validPassword: "Passwords dont match",
        verMas: "See more",
        version: "Version",
        versiones: "Versions",
        viewProfile: "View Profile",
        volver: "Back",
        warningInitial:
          "This mod hasn't sets for initial Deck, you must buy cards for build your Deck",
        warningRitual: "This version hasn't rituals",
        warninTower: "This mod hasn't Tower mode",
        welcomeToTea: "Welcome to TEA-ONLINE",
        wrongPassword: "Wrong Password",
        save: "save",
        selectyourwa: "Select WA_MRG.MRG",
        selectyourimage: "Select image",
      };
    },
    "38db": function (t, e, a) {},
    "3e8c": function (t, e, a) {
      "use strict";
      var n = a("79c9"),
        s = a.n(n);
      s.a;
    },
    "401f": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a(
            "div",
            { staticClass: "char-loader" },
            [
              t.showWarning
                ? a("div", { staticClass: "char-warning" }, [
                    a("p", [
                      t._v(
                        "This component does not edit the characters in the game, they are just an internal configuration. The editing should purely be done in another tool",
                      ),
                    ]),
                  ])
                : t._e(),
              a(
                "DragAndDrop",
                {
                  ref: "draganddrop",
                  attrs: {
                    id: "json-l",
                    "accepted-types": ".json",
                    "custom-content": !0,
                    "disable-click": !0,
                  },
                  on: {
                    onfileload: function (e) {
                      return t.cargarRoseta(e);
                    },
                  },
                },
                [
                  t.config.showSorted
                    ? t._e()
                    : a(
                        "div",
                        { staticClass: "char-container" },
                        [
                          t._l(t.roseta, function (e, n) {
                            return [
                              t.config.showAll ||
                              " " != t.roseta[n] ||
                              "l0" == n
                                ? a("div", { key: "r" + n }, [
                                    a("div", { staticClass: "char-cell" }, [
                                      a("div", [
                                        t._v(
                                          "\n                            " +
                                            t._s(t.showKey(n)) +
                                            "\n                        ",
                                        ),
                                      ]),
                                      a("input", {
                                        staticClass: "browser-default",
                                        attrs: { type: "text" },
                                        domProps: { value: t.roseta[n] },
                                        on: {
                                          change: function (e) {
                                            return t.validChange(e, n);
                                          },
                                        },
                                      }),
                                    ]),
                                  ])
                                : t._e(),
                            ];
                          }),
                        ],
                        2,
                      ),
                  t.config.showSorted
                    ? a(
                        "div",
                        { staticClass: "char-container" },
                        [
                          t._l(t.sortedkeys, function (e, n) {
                            return [
                              t.config.showAll ||
                              " " != t.roseta[e] ||
                              "l0" == e
                                ? a("div", { key: "r2" + n }, [
                                    a("div", { staticClass: "char-cell" }, [
                                      a("div", [
                                        t._v(
                                          "\n                            " +
                                            t._s(t.showKey(e)) +
                                            "\n                        ",
                                        ),
                                      ]),
                                      a("input", {
                                        staticClass: "browser-default",
                                        attrs: { type: "text" },
                                        domProps: { value: t.roseta[e] },
                                        on: {
                                          change: function (a) {
                                            return t.validChange(a, e);
                                          },
                                        },
                                      }),
                                    ]),
                                  ])
                                : t._e(),
                            ];
                          }),
                        ],
                        2,
                      )
                    : t._e(),
                  a("div", { staticClass: "char-actions" }, [
                    a("div", { staticClass: "char-actions-buttons" }, [
                      a(
                        "button",
                        {
                          staticClass: "browser-default",
                          on: { click: t.descargarRoseta },
                        },
                        [
                          a("font-awesome-icon", {
                            attrs: { icon: ["fas", "download"] },
                          }),
                          a("span", [t._v("Export json")]),
                        ],
                        1,
                      ),
                      a(
                        "button",
                        {
                          staticClass: "browser-default",
                          on: { click: t.triggerFileInput },
                        },
                        [
                          a("font-awesome-icon", {
                            attrs: { icon: ["fas", "upload"] },
                          }),
                          a("span", [t._v("Import json")]),
                        ],
                        1,
                      ),
                    ]),
                    a("div", { staticClass: "char-actions-switches" }, [
                      a("div", { staticClass: "switch" }, [
                        a("label", [
                          a("input", {
                            directives: [
                              {
                                name: "model",
                                rawName: "v-model",
                                value: t.config.showSorted,
                                expression: "config.showSorted",
                              },
                            ],
                            attrs: { type: "checkbox" },
                            domProps: {
                              checked: Array.isArray(t.config.showSorted)
                                ? t._i(t.config.showSorted, null) > -1
                                : t.config.showSorted,
                            },
                            on: {
                              change: function (e) {
                                var a = t.config.showSorted,
                                  n = e.target,
                                  s = !!n.checked;
                                if (Array.isArray(a)) {
                                  var r = null,
                                    i = t._i(a, r);
                                  n.checked
                                    ? i < 0 &&
                                      t.$set(
                                        t.config,
                                        "showSorted",
                                        a.concat([r]),
                                      )
                                    : i > -1 &&
                                      t.$set(
                                        t.config,
                                        "showSorted",
                                        a.slice(0, i).concat(a.slice(i + 1)),
                                      );
                                } else t.$set(t.config, "showSorted", s);
                              },
                            },
                          }),
                          a("span", { staticClass: "lever" }),
                          a("span", { staticClass: "tag-p" }, [t._v("Order")]),
                        ]),
                      ]),
                      a("div", { staticClass: "switch" }, [
                        a("label", [
                          a("input", {
                            directives: [
                              {
                                name: "model",
                                rawName: "v-model",
                                value: t.config.showAll,
                                expression: "config.showAll",
                              },
                            ],
                            attrs: { type: "checkbox" },
                            domProps: {
                              checked: Array.isArray(t.config.showAll)
                                ? t._i(t.config.showAll, null) > -1
                                : t.config.showAll,
                            },
                            on: {
                              change: function (e) {
                                var a = t.config.showAll,
                                  n = e.target,
                                  s = !!n.checked;
                                if (Array.isArray(a)) {
                                  var r = null,
                                    i = t._i(a, r);
                                  n.checked
                                    ? i < 0 &&
                                      t.$set(t.config, "showAll", a.concat([r]))
                                    : i > -1 &&
                                      t.$set(
                                        t.config,
                                        "showAll",
                                        a.slice(0, i).concat(a.slice(i + 1)),
                                      );
                                } else t.$set(t.config, "showAll", s);
                              },
                            },
                          }),
                          a("span", { staticClass: "lever" }),
                          a("span", { staticClass: "tag-p" }, [t._v("All")]),
                        ]),
                      ]),
                    ]),
                  ]),
                ],
              ),
            ],
            1,
          );
        },
        s = [],
        r = (a("6b54"), a("a481"), a("ac6a"), a("456d"), a("55dd"), a("d260")),
        i = a("ecee"),
        o = a("c074");
      i["c"].add(o["eb"], o["u"]);
      var c = {
          name: "CharLoader",
          components: { DragAndDrop: r["a"] },
          data: function () {
            return { config: { showSorted: !1, showAll: !1 } };
          },
          computed: {
            sortedkeys: function () {
              var t = this;
              return Object.keys(this.roseta).sort(function (e, a) {
                return t.roseta[e].charCodeAt(0) - t.roseta[a].charCodeAt(0);
              });
            },
          },
          props: {
            roseta: { type: Object, default: {} },
            showWarning: { type: Boolean, default: !0 },
          },
          methods: {
            showKey: function (t) {
              var e = t.replace("l", ""),
                a = 255 & parseInt(e);
              return ("00" + a.toString(16).toUpperCase()).slice(-2);
            },
            validChange: function (t, e) {
              (t.target.value.length > 1 &&
                (t.target.value = t.target.value.slice(0, 1)),
                0 == t.target.value.length && (t.target.value = " "),
                this.$set(this.roseta, e, t.target.value));
            },
            exportRoseta: function () {
              var t = {};
              for (var e in this.roseta) {
                var a = parseInt(e.replace("l", "")).toString(16).toUpperCase();
                ((a = ("00" + a).slice(-2)), (t[a] = this.roseta[e]));
              }
              return t;
            },
            importRoseta: function (t) {
              for (var e = {}, a = 0; a < 240; a++) {
                var n = a.toString(16).toUpperCase();
                ((n = ("00" + n).slice(-2)), (e["l" + a] = t[n] || " "));
              }
              return e;
            },
            descargarRoseta: function () {
              var t = this.exportRoseta(),
                e = JSON.stringify(t, null, 2),
                a = new Blob([e], { type: "application/json" }),
                n = URL.createObjectURL(a),
                s = document.createElement("a");
              ((s.href = n),
                (s.download = "charset.json"),
                s.click(),
                URL.revokeObjectURL(n));
            },
            cargarRoseta: function (t) {
              var e = this,
                a = t,
                n = new FileReader();
              ((n.onload = function (t) {
                var a = JSON.parse(t.target.result);
                e.$emit("new:roseta", e.importRoseta(a));
              }),
                n.readAsText(a));
            },
            triggerFileInput: function () {
              this.$refs.draganddrop &&
                this.$refs.draganddrop.triggerFileInput();
            },
          },
          watch: {
            roseta: {
              deep: !0,
              handler: function (t) {
                this.$emit("roseta", t);
              },
            },
          },
        },
        l = c,
        u = (a("11af"), a("2877")),
        d = Object(u["a"])(l, n, s, !1, null, "5342a20f", null);
      e["a"] = d.exports;
    },
    "40af": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", [
            a("div"),
            a("div", [
              a("ins", {
                staticClass: "adsbygoogle",
                staticStyle: { display: "block" },
                attrs: {
                  "data-ad-format": "fluid",
                  "data-ad-layout-key": t.llave,
                  "data-ad-client": "ca-pub-5969575583343092",
                  "data-ad-slot": t.casilla,
                },
              }),
            ]),
          ]);
        },
        s = [],
        r = {
          name: "Publicidad",
          props: { llave: String, casilla: String },
          mounted: function () {
            this.$nextTick(function () {
              (adsbygoogle = window.adsbygoogle || []).push({});
            });
          },
        },
        i = r,
        o = a("2877"),
        c = Object(o["a"])(i, n, s, !1, null, null, null);
      e["a"] = c.exports;
    },
    "4a23": function (t, e, a) {
      "use strict";
      var n = a("5067"),
        s = a.n(n);
      s.a;
    },
    "4b1a": function (t, e, a) {
      "use strict";
      var n = a("4d8a"),
        s = a.n(n);
      s.a;
    },
    "4d8a": function (t, e, a) {},
    "4ec0": function (t, e, a) {
      "use strict";
      var n = a("877b"),
        s = a.n(n);
      s.a;
    },
    5067: function (t, e, a) {},
    5191: function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a(
            "div",
            { staticClass: "pxt-root" },
            [
              a("div", { staticClass: "pxt-body" }, [
                a(
                  "aside",
                  { staticClass: "pxt-sidebar scrpe" },
                  [
                    a("section", { staticClass: "pxt-panel" }, [
                      a(
                        "h2",
                        { staticClass: "pxt-panel-title" },
                        [
                          a("font-awesome-icon", { attrs: { icon: "image" } }),
                          t._v(" Source image"),
                        ],
                        1,
                      ),
                      a(
                        "div",
                        {
                          staticClass: "pxt-dropzone",
                          class: { "pxt-dropzone--active": t.isDraggingFile },
                          on: {
                            click: function (e) {
                              return t.$refs.fileInput.click();
                            },
                            dragover: function (e) {
                              (e.preventDefault(), (t.isDraggingFile = !0));
                            },
                            dragleave: function (e) {
                              (e.preventDefault(), (t.isDraggingFile = !1));
                            },
                            drop: function (e) {
                              return (e.preventDefault(), t.onDrop(e));
                            },
                          },
                        },
                        [
                          a("input", {
                            ref: "fileInput",
                            staticClass: "pxt-hidden-input",
                            attrs: { type: "file", accept: "image/*" },
                            on: { change: t.onFileInputChange },
                          }),
                          a("font-awesome-icon", {
                            staticClass: "pxt-dropzone-icon",
                            attrs: { icon: "cloud-upload-alt" },
                          }),
                          t.hasImage
                            ? a("p", { staticClass: "pxt-dropzone-text" }, [
                                t._v(
                                  "\n                        " +
                                    t._s(t.srcW) +
                                    "x" +
                                    t._s(t.srcH) +
                                    "px loaded — click to replace\n                    ",
                                ),
                              ])
                            : a("p", { staticClass: "pxt-dropzone-text" }, [
                                t._v(
                                  "\n                        Drop an image, click to browse, or paste with ",
                                ),
                                a("b", [t._v("Ctrl+V")]),
                              ]),
                        ],
                        1,
                      ),
                      a(
                        "button",
                        {
                          staticClass:
                            "pxt-btn pxt-btn--ghost pxt-btn--block pxt-btn--spaced",
                          attrs: { type: "button" },
                          on: {
                            click: function (e) {
                              t.catalogVisible = !0;
                            },
                          },
                        },
                        [
                          a("font-awesome-icon", { attrs: { icon: "images" } }),
                          t._v(" Browse catalog\n                "),
                        ],
                        1,
                      ),
                    ]),
                    t.hasImage
                      ? [
                          a("section", { staticClass: "pxt-panel" }, [
                            a(
                              "h2",
                              { staticClass: "pxt-panel-title" },
                              [
                                a("font-awesome-icon", {
                                  attrs: { icon: "crop-alt" },
                                }),
                                t._v(" Selection"),
                              ],
                              1,
                            ),
                            a("div", { staticClass: "pxt-tabset" }, [
                              a(
                                "button",
                                {
                                  staticClass: "pxt-tab",
                                  class: {
                                    "pxt-tab--active": "free" === t.cropMode,
                                  },
                                  attrs: { type: "button" },
                                  on: {
                                    click: function (e) {
                                      return t.setCropMode("free");
                                    },
                                  },
                                },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "vector-square" },
                                  }),
                                  a("span", [t._v("Free")]),
                                ],
                                1,
                              ),
                              a(
                                "button",
                                {
                                  staticClass: "pxt-tab",
                                  class: {
                                    "pxt-tab--active": "fixed" === t.cropMode,
                                  },
                                  attrs: { type: "button" },
                                  on: {
                                    click: function (e) {
                                      return t.setCropMode("fixed");
                                    },
                                  },
                                },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "lock" },
                                  }),
                                  a("span", [t._v("Locked ratio")]),
                                ],
                                1,
                              ),
                            ]),
                            a("div", { staticClass: "pxt-grid4" }, [
                              a("label", { staticClass: "pxt-field" }, [
                                a("span", { staticClass: "pxt-lbl" }, [
                                  t._v("X"),
                                ]),
                                a("input", {
                                  directives: [
                                    {
                                      name: "model",
                                      rawName: "v-model.number",
                                      value: t.crop.x,
                                      expression: "crop.x",
                                      modifiers: { number: !0 },
                                    },
                                  ],
                                  staticClass: "browser-default pxt-input",
                                  attrs: { type: "number" },
                                  domProps: { value: t.crop.x },
                                  on: {
                                    change: function (e) {
                                      return t.onCropFieldChange("x");
                                    },
                                    input: function (e) {
                                      e.target.composing ||
                                        t.$set(
                                          t.crop,
                                          "x",
                                          t._n(e.target.value),
                                        );
                                    },
                                    blur: function (e) {
                                      return t.$forceUpdate();
                                    },
                                  },
                                }),
                              ]),
                              a("label", { staticClass: "pxt-field" }, [
                                a("span", { staticClass: "pxt-lbl" }, [
                                  t._v("Y"),
                                ]),
                                a("input", {
                                  directives: [
                                    {
                                      name: "model",
                                      rawName: "v-model.number",
                                      value: t.crop.y,
                                      expression: "crop.y",
                                      modifiers: { number: !0 },
                                    },
                                  ],
                                  staticClass: "browser-default pxt-input",
                                  attrs: { type: "number" },
                                  domProps: { value: t.crop.y },
                                  on: {
                                    change: function (e) {
                                      return t.onCropFieldChange("y");
                                    },
                                    input: function (e) {
                                      e.target.composing ||
                                        t.$set(
                                          t.crop,
                                          "y",
                                          t._n(e.target.value),
                                        );
                                    },
                                    blur: function (e) {
                                      return t.$forceUpdate();
                                    },
                                  },
                                }),
                              ]),
                              a("label", { staticClass: "pxt-field" }, [
                                a("span", { staticClass: "pxt-lbl" }, [
                                  t._v("W"),
                                ]),
                                a("input", {
                                  directives: [
                                    {
                                      name: "model",
                                      rawName: "v-model.number",
                                      value: t.crop.w,
                                      expression: "crop.w",
                                      modifiers: { number: !0 },
                                    },
                                  ],
                                  staticClass: "browser-default pxt-input",
                                  attrs: { type: "number" },
                                  domProps: { value: t.crop.w },
                                  on: {
                                    change: function (e) {
                                      return t.onCropFieldChange("w");
                                    },
                                    input: function (e) {
                                      e.target.composing ||
                                        t.$set(
                                          t.crop,
                                          "w",
                                          t._n(e.target.value),
                                        );
                                    },
                                    blur: function (e) {
                                      return t.$forceUpdate();
                                    },
                                  },
                                }),
                              ]),
                              a("label", { staticClass: "pxt-field" }, [
                                a("span", { staticClass: "pxt-lbl" }, [
                                  t._v("H"),
                                ]),
                                a("input", {
                                  directives: [
                                    {
                                      name: "model",
                                      rawName: "v-model.number",
                                      value: t.crop.h,
                                      expression: "crop.h",
                                      modifiers: { number: !0 },
                                    },
                                  ],
                                  staticClass: "browser-default pxt-input",
                                  attrs: { type: "number" },
                                  domProps: { value: t.crop.h },
                                  on: {
                                    change: function (e) {
                                      return t.onCropFieldChange("h");
                                    },
                                    input: function (e) {
                                      e.target.composing ||
                                        t.$set(
                                          t.crop,
                                          "h",
                                          t._n(e.target.value),
                                        );
                                    },
                                    blur: function (e) {
                                      return t.$forceUpdate();
                                    },
                                  },
                                }),
                              ]),
                            ]),
                            a("div", { staticClass: "pxt-btnrow" }, [
                              a(
                                "button",
                                {
                                  staticClass: "pxt-btn pxt-btn--ghost",
                                  attrs: { type: "button" },
                                  on: { click: t.selectAll },
                                },
                                [t._v("Select all")],
                              ),
                              a(
                                "button",
                                {
                                  staticClass: "pxt-btn pxt-btn--ghost",
                                  attrs: { type: "button" },
                                  on: { click: t.matchAspect },
                                },
                                [
                                  t._v(
                                    "Fit to output\n                            ratio",
                                  ),
                                ],
                              ),
                            ]),
                            a(
                              "p",
                              { staticClass: "pxt-hint" },
                              [
                                "fixed" === t.cropMode
                                  ? [
                                      t._v(
                                        "\n                            The selection always matches the output ratio, so the chosen area is never distorted.\n                            Drag inside the box to move it, or its bottom-right corner to resize it.\n                        ",
                                      ),
                                    ]
                                  : [
                                      t._v(
                                        "\n                            Drag on the image to draw a selection, or edit the fields above (any ratio is fine).\n                        ",
                                      ),
                                    ],
                              ],
                              2,
                            ),
                          ]),
                          a("section", { staticClass: "pxt-panel" }, [
                            a(
                              "h2",
                              { staticClass: "pxt-panel-title" },
                              [
                                a("font-awesome-icon", {
                                  attrs: { icon: "expand-arrows-alt" },
                                }),
                                t._v(" Output size"),
                              ],
                              1,
                            ),
                            a("div", { staticClass: "pxt-grid2" }, [
                              a("label", { staticClass: "pxt-field" }, [
                                a("span", { staticClass: "pxt-lbl" }, [
                                  t._v("Width (px)"),
                                ]),
                                a("input", {
                                  directives: [
                                    {
                                      name: "model",
                                      rawName: "v-model.number",
                                      value: t.widthLocal,
                                      expression: "widthLocal",
                                      modifiers: { number: !0 },
                                    },
                                  ],
                                  staticClass: "browser-default pxt-input",
                                  attrs: {
                                    type: "number",
                                    min: "1",
                                    max: "1024",
                                    disabled: t.widthLocked,
                                  },
                                  domProps: { value: t.widthLocal },
                                  on: {
                                    change: t.onSizeChange,
                                    input: function (e) {
                                      e.target.composing ||
                                        (t.widthLocal = t._n(e.target.value));
                                    },
                                    blur: function (e) {
                                      return t.$forceUpdate();
                                    },
                                  },
                                }),
                              ]),
                              a("label", { staticClass: "pxt-field" }, [
                                a("span", { staticClass: "pxt-lbl" }, [
                                  t._v("Height (px)"),
                                ]),
                                a("input", {
                                  directives: [
                                    {
                                      name: "model",
                                      rawName: "v-model.number",
                                      value: t.heightLocal,
                                      expression: "heightLocal",
                                      modifiers: { number: !0 },
                                    },
                                  ],
                                  staticClass: "browser-default pxt-input",
                                  attrs: {
                                    type: "number",
                                    min: "1",
                                    max: "1024",
                                    disabled: t.heightLocked,
                                  },
                                  domProps: { value: t.heightLocal },
                                  on: {
                                    change: t.onSizeChange,
                                    input: function (e) {
                                      e.target.composing ||
                                        (t.heightLocal = t._n(e.target.value));
                                    },
                                    blur: function (e) {
                                      return t.$forceUpdate();
                                    },
                                  },
                                }),
                              ]),
                            ]),
                            t.widthLocked || t.heightLocked
                              ? a("p", { staticClass: "pxt-hint" }, [
                                  t._v(
                                    "Size is fixed by the app for this tool.\n                    ",
                                  ),
                                ])
                              : a(
                                  "div",
                                  { staticClass: "pxt-tagset" },
                                  t._l(t.sizePresets, function (e) {
                                    return a(
                                      "button",
                                      {
                                        key: e.label,
                                        staticClass: "pxt-tag",
                                        attrs: { type: "button" },
                                        on: {
                                          click: function (a) {
                                            return t.applyPreset(e.w, e.h);
                                          },
                                        },
                                      },
                                      [t._v(t._s(e.label))],
                                    );
                                  }),
                                  0,
                                ),
                            a(
                              "label",
                              { staticClass: "pxt-field pxt-field--spaced" },
                              [
                                a("span", { staticClass: "pxt-lbl" }, [
                                  t._v("Resize algorithm"),
                                ]),
                                a(
                                  "details",
                                  {
                                    ref: "algoDropdown",
                                    staticClass: "pxt-dropdown",
                                  },
                                  [
                                    a(
                                      "summary",
                                      { staticClass: "pxt-dropdown-summary" },
                                      [
                                        a("span", [
                                          t._v(t._s(t.resizeAlgoLabel)),
                                        ]),
                                        a("font-awesome-icon", {
                                          attrs: { icon: "chevron-down" },
                                        }),
                                      ],
                                      1,
                                    ),
                                    a(
                                      "ul",
                                      { staticClass: "pxt-dropdown-list" },
                                      t._l(t.resizeAlgoOptions, function (e) {
                                        return a(
                                          "li",
                                          {
                                            key: e.value,
                                            staticClass: "pxt-dropdown-item",
                                            class: {
                                              "pxt-dropdown-item--active":
                                                t.resizeAlgo === e.value,
                                            },
                                            on: {
                                              click: function (a) {
                                                return t.selectResizeAlgo(
                                                  e.value,
                                                );
                                              },
                                            },
                                          },
                                          [
                                            a("b", [t._v(t._s(e.title))]),
                                            e.desc
                                              ? a("span", [
                                                  t._v(" — " + t._s(e.desc)),
                                                ])
                                              : t._e(),
                                          ],
                                        );
                                      }),
                                      0,
                                    ),
                                  ],
                                ),
                              ],
                            ),
                            t._m(0),
                          ]),
                          a(
                            "section",
                            { staticClass: "pxt-panel" },
                            [
                              a(
                                "h2",
                                { staticClass: "pxt-panel-title" },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "palette" },
                                  }),
                                  t._v(
                                    "\n                        Color palette\n                    ",
                                  ),
                                ],
                                1,
                              ),
                              t.colorsLocked
                                ? a("p", { staticClass: "pxt-hint" }, [
                                    t._v(
                                      t._s(t.colorsLocal) +
                                        " colors — fixed by the app for this tool.",
                                    ),
                                  ])
                                : [
                                    a("div", { staticClass: "pxt-stepper" }, [
                                      a(
                                        "button",
                                        {
                                          staticClass: "pxt-stepper-btn",
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              return t.stepColors(-1);
                                            },
                                          },
                                        },
                                        [
                                          a("font-awesome-icon", {
                                            attrs: { icon: "minus" },
                                          }),
                                        ],
                                        1,
                                      ),
                                      a("input", {
                                        directives: [
                                          {
                                            name: "model",
                                            rawName: "v-model.number",
                                            value: t.colorsLocal,
                                            expression: "colorsLocal",
                                            modifiers: { number: !0 },
                                          },
                                        ],
                                        staticClass:
                                          "browser-default pxt-input pxt-stepper-input",
                                        attrs: {
                                          type: "number",
                                          min: "2",
                                          max: "256",
                                        },
                                        domProps: { value: t.colorsLocal },
                                        on: {
                                          change: t.clampColors,
                                          input: function (e) {
                                            e.target.composing ||
                                              (t.colorsLocal = t._n(
                                                e.target.value,
                                              ));
                                          },
                                          blur: function (e) {
                                            return t.$forceUpdate();
                                          },
                                        },
                                      }),
                                      a(
                                        "button",
                                        {
                                          staticClass: "pxt-stepper-btn",
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              return t.stepColors(1);
                                            },
                                          },
                                        },
                                        [
                                          a("font-awesome-icon", {
                                            attrs: { icon: "plus" },
                                          }),
                                        ],
                                        1,
                                      ),
                                      a(
                                        "span",
                                        { staticClass: "pxt-stepper-suffix" },
                                        [t._v("colors")],
                                      ),
                                    ]),
                                    a("div", { staticClass: "pxt-tagset" }, [
                                      a(
                                        "button",
                                        {
                                          staticClass: "pxt-tag",
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              t.colorsLocal = 16;
                                            },
                                          },
                                        },
                                        [t._v("16 (2ppb)")],
                                      ),
                                      a(
                                        "button",
                                        {
                                          staticClass: "pxt-tag",
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              t.colorsLocal = 72;
                                            },
                                          },
                                        },
                                        [t._v("72 (1ppb)")],
                                      ),
                                      a(
                                        "button",
                                        {
                                          staticClass: "pxt-tag",
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              t.colorsLocal = 256;
                                            },
                                          },
                                        },
                                        [t._v("256 (8bpp)")],
                                      ),
                                    ]),
                                  ],
                            ],
                            2,
                          ),
                          a("section", { staticClass: "pxt-panel" }, [
                            a(
                              "h2",
                              { staticClass: "pxt-panel-title" },
                              [
                                a("font-awesome-icon", {
                                  attrs: { icon: "lightbulb" },
                                }),
                                t._v(
                                  "\n                        Edge smoothing\n                    ",
                                ),
                              ],
                              1,
                            ),
                            a(
                              "label",
                              { staticClass: "pxt-field pxt-field--spaced" },
                              [
                                a("span", { staticClass: "pxt-lbl" }, [
                                  t._v("Intensity"),
                                ]),
                                a(
                                  "div",
                                  { staticClass: "pxt-tabset pxt-tabset--4" },
                                  t._l(
                                    ["None", "Light", "Medium", "Strong"],
                                    function (e, n) {
                                      return a(
                                        "button",
                                        {
                                          key: n,
                                          staticClass: "pxt-tab",
                                          class: {
                                            "pxt-tab--active":
                                              t.edgeSmoothing === n,
                                          },
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              t.edgeSmoothing = n;
                                            },
                                          },
                                        },
                                        [t._v(t._s(e))],
                                      );
                                    },
                                  ),
                                  0,
                                ),
                              ],
                            ),
                            a("p", { staticClass: "pxt-hint" }, [
                              t._v(
                                "\n                        Blurs the resized image slightly before the colors are locked in, softening jagged staircase\n                        edges. Higher settings look softer — pairs well with Floyd-Steinberg or Ordered dithering\n                        below.\n                    ",
                              ),
                            ]),
                          ]),
                          a(
                            "section",
                            {
                              staticClass: "pxt-panel",
                              staticStyle: { "padding-bottom": "0em" },
                            },
                            [
                              a(
                                "h2",
                                { staticClass: "pxt-panel-title" },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "spray-can" },
                                  }),
                                  t._v(
                                    "\n                        Dithering\n                    ",
                                  ),
                                ],
                                1,
                              ),
                              a(
                                "label",
                                { staticClass: "pxt-field pxt-field--spaced" },
                                [
                                  a("span", { staticClass: "pxt-lbl" }, [
                                    t._v("Dithering algorithm"),
                                  ]),
                                  a(
                                    "details",
                                    {
                                      ref: "ditherDropdown",
                                      staticClass: "pxt-dropdown",
                                    },
                                    [
                                      a(
                                        "summary",
                                        { staticClass: "pxt-dropdown-summary" },
                                        [
                                          a("span", [
                                            t._v(t._s(t.ditherLabel)),
                                          ]),
                                          a("font-awesome-icon", {
                                            attrs: { icon: "chevron-down" },
                                          }),
                                        ],
                                        1,
                                      ),
                                      a(
                                        "ul",
                                        { staticClass: "pxt-dropdown-list" },
                                        t._l(t.ditherOptions, function (e) {
                                          return a(
                                            "li",
                                            {
                                              key: e.value,
                                              staticClass: "pxt-dropdown-item",
                                              class: {
                                                "pxt-dropdown-item--active":
                                                  t.ditherMode === e.value,
                                              },
                                              on: {
                                                click: function (a) {
                                                  return t.selectDither(
                                                    e.value,
                                                  );
                                                },
                                              },
                                            },
                                            [
                                              a("b", [t._v(t._s(e.title))]),
                                              e.desc
                                                ? a("span", [
                                                    t._v(" — " + t._s(e.desc)),
                                                  ])
                                                : t._e(),
                                            ],
                                          );
                                        }),
                                        0,
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                              a("p", { staticClass: "pxt-hint" }, [
                                t._v(
                                  "\n                        16 and 256 colors match the typical PSX CLUT depths (4bpp / 8bpp). Any pixel with\n                        transparency\n                        reserves one palette slot as the color-key.\n                    ",
                                ),
                              ]),
                            ],
                          ),
                          a(
                            "section",
                            { staticClass: "pxt-panel pxt-panel--last" },
                            [
                              t.isProcessing
                                ? a(
                                    "div",
                                    {
                                      staticClass:
                                        "pxt-processing animated fadeIn",
                                    },
                                    [
                                      a("font-awesome-icon", {
                                        attrs: { icon: "spinner", spin: "" },
                                      }),
                                      a("span", [t._v("Processing…")]),
                                    ],
                                    1,
                                  )
                                : t._e(),
                              a(
                                "button",
                                {
                                  staticClass:
                                    "pxt-btn pxt-btn--primary pxt-btn--block",
                                  attrs: {
                                    type: "button",
                                    disabled: t.isProcessing,
                                  },
                                  on: { click: t.generate },
                                },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "magic" },
                                  }),
                                  t._v(" Generate image\n                    "),
                                ],
                                1,
                              ),
                            ],
                          ),
                        ]
                      : t._e(),
                  ],
                  2,
                ),
                a("div", { staticClass: "pxt-main" }, [
                  a("div", { staticClass: "pxt-workspace" }, [
                    a("div", { staticClass: "pxt-stage" }, [
                      a("div", { staticClass: "pxt-stage-title" }, [
                        a("h3", [t._v("Original + selection")]),
                        a("div", { staticClass: "pxt-stage-title-right" }, [
                          a("span", [
                            t._v(
                              t._s(
                                t.hasImage ? t.srcW + "x" + t.srcH + "px" : "",
                              ),
                            ),
                          ]),
                          t.hasImage
                            ? a("div", { staticClass: "pxt-zoom-controls" }, [
                                a(
                                  "button",
                                  {
                                    staticClass: "pxt-zoom-btn",
                                    attrs: {
                                      type: "button",
                                      disabled: 0 === t.zoomIndex,
                                      title: "Zoom out",
                                    },
                                    on: { click: t.zoomOut },
                                  },
                                  [
                                    a("font-awesome-icon", {
                                      attrs: { icon: "search-minus" },
                                    }),
                                  ],
                                  1,
                                ),
                                a("span", { staticClass: "pxt-zoom-pct" }, [
                                  t._v(t._s(t.zoomPercent) + "%"),
                                ]),
                                a(
                                  "button",
                                  {
                                    staticClass: "pxt-zoom-btn",
                                    attrs: {
                                      type: "button",
                                      disabled:
                                        t.zoomIndex === t.zoomSteps.length - 1,
                                      title: "Zoom in",
                                    },
                                    on: { click: t.zoomIn },
                                  },
                                  [
                                    a("font-awesome-icon", {
                                      attrs: { icon: "search-plus" },
                                    }),
                                  ],
                                  1,
                                ),
                                t.zoomLevel > 1
                                  ? a(
                                      "button",
                                      {
                                        staticClass: "pxt-zoom-btn",
                                        attrs: {
                                          type: "button",
                                          title: "Fit to view",
                                        },
                                        on: { click: t.resetZoom },
                                      },
                                      [
                                        a("font-awesome-icon", {
                                          attrs: { icon: "compress" },
                                        }),
                                      ],
                                      1,
                                    )
                                  : t._e(),
                                t.zoomLevel > 1
                                  ? a(
                                      "button",
                                      {
                                        staticClass: "pxt-zoom-btn",
                                        class: {
                                          "pxt-zoom-btn--active":
                                            "pan" === t.interactionMode,
                                        },
                                        attrs: {
                                          type: "button",
                                          title: "Pan (drag to move the view)",
                                        },
                                        on: { click: t.togglePan },
                                      },
                                      [
                                        a("font-awesome-icon", {
                                          attrs: { icon: "hand-paper" },
                                        }),
                                      ],
                                      1,
                                    )
                                  : t._e(),
                              ])
                            : t._e(),
                        ]),
                      ]),
                      a(
                        "div",
                        { ref: "origWrap", staticClass: "pxt-canvas-wrap" },
                        [
                          a("canvas", {
                            directives: [
                              {
                                name: "show",
                                rawName: "v-show",
                                value: t.hasImage,
                                expression: "hasImage",
                              },
                            ],
                            ref: "origCanvas",
                            staticClass: "pxt-orig-canvas",
                            on: {
                              mousedown: t.onCanvasMouseDown,
                              mousemove: t.onCanvasHoverMove,
                              touchstart: t.onCanvasTouchStart,
                            },
                          }),
                          t.hasImage
                            ? t._e()
                            : a("p", { staticClass: "pxt-empty-msg" }, [
                                t._v("Load an image to get started"),
                              ]),
                        ],
                      ),
                      t.hasImage
                        ? a("div", { staticClass: "pxt-stage-foot" }, [
                            t._v(
                              "\n                        Selection: " +
                                t._s(t.crop.w) +
                                "x" +
                                t._s(t.crop.h) +
                                "px at (" +
                                t._s(t.crop.x) +
                                ", " +
                                t._s(t.crop.y) +
                                ")\n                    ",
                            ),
                          ])
                        : t._e(),
                    ]),
                    a("div", { staticClass: "pxt-stage" }, [
                      a("div", { staticClass: "pxt-stage-title" }, [
                        a("h3", [t._v("Indexed result")]),
                        a("div", { staticClass: "pxt-stage-title-right" }, [
                          a("span", [
                            t._v(t._s(t.hasResult ? t.resultDims : "")),
                          ]),
                          t.hasResult
                            ? a("div", { staticClass: "pxt-zoom-controls" }, [
                                a(
                                  "button",
                                  {
                                    staticClass: "pxt-zoom-btn",
                                    attrs: {
                                      type: "button",
                                      disabled: 0 === t.resultZoomIndex,
                                      title: "Zoom out",
                                    },
                                    on: { click: t.resultZoomOut },
                                  },
                                  [
                                    a("font-awesome-icon", {
                                      attrs: { icon: "search-minus" },
                                    }),
                                  ],
                                  1,
                                ),
                                a("span", { staticClass: "pxt-zoom-pct" }, [
                                  t._v(t._s(t.resultZoomPercent) + "%"),
                                ]),
                                a(
                                  "button",
                                  {
                                    staticClass: "pxt-zoom-btn",
                                    attrs: {
                                      type: "button",
                                      disabled:
                                        t.resultZoomIndex ===
                                        t.resultZoomSteps.length - 1,
                                      title: "Zoom in",
                                    },
                                    on: { click: t.resultZoomIn },
                                  },
                                  [
                                    a("font-awesome-icon", {
                                      attrs: { icon: "search-plus" },
                                    }),
                                  ],
                                  1,
                                ),
                                t.resultZoomLevel > 1
                                  ? a(
                                      "button",
                                      {
                                        staticClass: "pxt-zoom-btn",
                                        attrs: {
                                          type: "button",
                                          title: "Fit to view",
                                        },
                                        on: { click: t.resultResetZoom },
                                      },
                                      [
                                        a("font-awesome-icon", {
                                          attrs: { icon: "compress" },
                                        }),
                                      ],
                                      1,
                                    )
                                  : t._e(),
                                t.resultZoomLevel > 1
                                  ? a(
                                      "button",
                                      {
                                        staticClass: "pxt-zoom-btn",
                                        class: {
                                          "pxt-zoom-btn--active":
                                            "pan" === t.resultInteractionMode,
                                        },
                                        attrs: {
                                          type: "button",
                                          title: "Pan (drag to move the view)",
                                        },
                                        on: { click: t.toggleResultPan },
                                      },
                                      [
                                        a("font-awesome-icon", {
                                          attrs: { icon: "hand-paper" },
                                        }),
                                      ],
                                      1,
                                    )
                                  : t._e(),
                              ])
                            : t._e(),
                        ]),
                      ]),
                      a(
                        "div",
                        { ref: "resultWrap", staticClass: "pxt-canvas-wrap" },
                        [
                          a(
                            "transition",
                            {
                              attrs: {
                                "enter-active-class": "animated fadeIn",
                              },
                            },
                            [
                              t.hasResult
                                ? a("canvas", {
                                    ref: "resultCanvas",
                                    staticClass: "pxt-result-canvas",
                                    on: {
                                      click: t.onResultCanvasClick,
                                      mousedown: t.onResultMouseDown,
                                      mousemove: t.onResultHoverMove,
                                      touchstart: t.onResultTouchStart,
                                    },
                                  })
                                : t._e(),
                            ],
                          ),
                          t.hasResult
                            ? t._e()
                            : a("p", { staticClass: "pxt-empty-msg" }, [
                                t._v("Generate the image to see the result"),
                              ]),
                          t.canUndoBg
                            ? a(
                                "button",
                                {
                                  staticClass: "pxt-undo-fab animated fadeIn",
                                  attrs: {
                                    type: "button",
                                    title: "Undo (Ctrl+Z)",
                                  },
                                  on: { click: t.undoEdit },
                                },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "undo" },
                                  }),
                                ],
                                1,
                              )
                            : t._e(),
                        ],
                        1,
                      ),
                      t.hasResult
                        ? a("div", { staticClass: "pxt-stage-foot" }, [
                            t._v(
                              "\n                        Zoom in for precise clicks — use the pan tool (hand icon) if the area you want\n                        to click has scrolled out of view.\n                    ",
                            ),
                          ])
                        : t._e(),
                      t.hasResult
                        ? a(
                            "div",
                            { staticClass: "pxt-palette-strip" },
                            t._l(t.resultPalette, function (e, n) {
                              return a("span", {
                                key: n,
                                staticClass: "pxt-swatch",
                                class: {
                                  "pxt-swatch--transparent":
                                    n === t.resultTransparentIndex,
                                },
                                style: t.swatchStyle(n),
                                attrs: {
                                  title:
                                    "#" +
                                    n +
                                    ": rgb(" +
                                    e[0] +
                                    "," +
                                    e[1] +
                                    "," +
                                    e[2] +
                                    ")",
                                },
                              });
                            }),
                            0,
                          )
                        : t._e(),
                      t.hasResult
                        ? a("div", { staticClass: "pxt-status" }, [
                            t._v(t._s(t.resultStatus)),
                          ])
                        : t._e(),
                      t.hasResult
                        ? a(
                            "div",
                            { staticClass: "pxt-bg-tool" },
                            [
                              a(
                                "h2",
                                { staticClass: "pxt-panel-title" },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "spray-can" },
                                  }),
                                  t._v(" Remove background"),
                                ],
                                1,
                              ),
                              a(
                                "div",
                                { staticClass: "pxt-tabset pxt-tabset--3" },
                                [
                                  a(
                                    "button",
                                    {
                                      staticClass: "pxt-tab",
                                      class: {
                                        "pxt-tab--active":
                                          "color" === t.bgRemovalMode,
                                      },
                                      attrs: { type: "button" },
                                      on: {
                                        click: function (e) {
                                          t.bgRemovalMode = "color";
                                        },
                                      },
                                    },
                                    [
                                      a("font-awesome-icon", {
                                        attrs: { icon: "spray-can" },
                                      }),
                                      a("span", [t._v("Click color")]),
                                    ],
                                    1,
                                  ),
                                  a(
                                    "button",
                                    {
                                      staticClass: "pxt-tab",
                                      class: {
                                        "pxt-tab--active":
                                          "smart" === t.bgRemovalMode,
                                      },
                                      attrs: { type: "button" },
                                      on: {
                                        click: function (e) {
                                          t.bgRemovalMode = "smart";
                                        },
                                      },
                                    },
                                    [
                                      a("font-awesome-icon", {
                                        attrs: { icon: "lightbulb" },
                                      }),
                                      a("span", [t._v("Smart block")]),
                                    ],
                                    1,
                                  ),
                                  a(
                                    "button",
                                    {
                                      staticClass: "pxt-tab",
                                      class: {
                                        "pxt-tab--active":
                                          "eraser" === t.bgRemovalMode,
                                      },
                                      attrs: { type: "button" },
                                      on: {
                                        click: function (e) {
                                          t.bgRemovalMode = "eraser";
                                        },
                                      },
                                    },
                                    [
                                      a("font-awesome-icon", {
                                        attrs: { icon: "eraser" },
                                      }),
                                      a("span", [t._v("Eraser")]),
                                    ],
                                    1,
                                  ),
                                ],
                              ),
                              "eraser" !== t.bgRemovalMode
                                ? [
                                    a("div", { staticClass: "pxt-stepper" }, [
                                      a(
                                        "button",
                                        {
                                          staticClass: "pxt-stepper-btn",
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              t.bgTolerance = Math.max(
                                                0,
                                                t.bgTolerance - 5,
                                              );
                                            },
                                          },
                                        },
                                        [
                                          a("font-awesome-icon", {
                                            attrs: { icon: "minus" },
                                          }),
                                        ],
                                        1,
                                      ),
                                      a("input", {
                                        directives: [
                                          {
                                            name: "model",
                                            rawName: "v-model.number",
                                            value: t.bgTolerance,
                                            expression: "bgTolerance",
                                            modifiers: { number: !0 },
                                          },
                                        ],
                                        staticClass:
                                          "browser-default pxt-input pxt-stepper-input",
                                        attrs: {
                                          type: "number",
                                          min: "0",
                                          max: "100",
                                        },
                                        domProps: { value: t.bgTolerance },
                                        on: {
                                          input: function (e) {
                                            e.target.composing ||
                                              (t.bgTolerance = t._n(
                                                e.target.value,
                                              ));
                                          },
                                          blur: function (e) {
                                            return t.$forceUpdate();
                                          },
                                        },
                                      }),
                                      a(
                                        "button",
                                        {
                                          staticClass: "pxt-stepper-btn",
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              t.bgTolerance = Math.min(
                                                100,
                                                t.bgTolerance + 5,
                                              );
                                            },
                                          },
                                        },
                                        [
                                          a("font-awesome-icon", {
                                            attrs: { icon: "plus" },
                                          }),
                                        ],
                                        1,
                                      ),
                                      a(
                                        "span",
                                        { staticClass: "pxt-stepper-suffix" },
                                        [t._v("tolerance")],
                                      ),
                                    ]),
                                    a(
                                      "p",
                                      { staticClass: "pxt-hint" },
                                      [
                                        t._v(
                                          "\n                                Click a pixel on the result above to remove it.\n                                ",
                                        ),
                                        "color" === t.bgRemovalMode
                                          ? [
                                              t._v(
                                                "Every pixel with a matching color\n                                    turns transparent, anywhere in the image.",
                                              ),
                                            ]
                                          : [
                                              t._v(
                                                "Only the connected block of matching color touching your\n                                    click turns transparent.",
                                              ),
                                            ],
                                      ],
                                      2,
                                    ),
                                  ]
                                : [
                                    a("div", { staticClass: "pxt-stepper" }, [
                                      a(
                                        "button",
                                        {
                                          staticClass: "pxt-stepper-btn",
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              t.eraserSize = Math.max(
                                                1,
                                                t.eraserSize - 1,
                                              );
                                            },
                                          },
                                        },
                                        [
                                          a("font-awesome-icon", {
                                            attrs: { icon: "minus" },
                                          }),
                                        ],
                                        1,
                                      ),
                                      a("input", {
                                        directives: [
                                          {
                                            name: "model",
                                            rawName: "v-model.number",
                                            value: t.eraserSize,
                                            expression: "eraserSize",
                                            modifiers: { number: !0 },
                                          },
                                        ],
                                        staticClass:
                                          "browser-default pxt-input pxt-stepper-input",
                                        attrs: {
                                          type: "number",
                                          min: "1",
                                          max: "80",
                                        },
                                        domProps: { value: t.eraserSize },
                                        on: {
                                          input: function (e) {
                                            e.target.composing ||
                                              (t.eraserSize = t._n(
                                                e.target.value,
                                              ));
                                          },
                                          blur: function (e) {
                                            return t.$forceUpdate();
                                          },
                                        },
                                      }),
                                      a(
                                        "button",
                                        {
                                          staticClass: "pxt-stepper-btn",
                                          attrs: { type: "button" },
                                          on: {
                                            click: function (e) {
                                              t.eraserSize = Math.min(
                                                80,
                                                t.eraserSize + 1,
                                              );
                                            },
                                          },
                                        },
                                        [
                                          a("font-awesome-icon", {
                                            attrs: { icon: "plus" },
                                          }),
                                        ],
                                        1,
                                      ),
                                      a(
                                        "span",
                                        { staticClass: "pxt-stepper-suffix" },
                                        [t._v("brush size")],
                                      ),
                                    ]),
                                    a(
                                      "div",
                                      {
                                        staticClass: "pxt-stepper",
                                        staticStyle: { "margin-top": "8px" },
                                      },
                                      [
                                        a(
                                          "button",
                                          {
                                            staticClass: "pxt-stepper-btn",
                                            attrs: { type: "button" },
                                            on: {
                                              click: function (e) {
                                                t.eraserHardness = Math.max(
                                                  0,
                                                  t.eraserHardness - 10,
                                                );
                                              },
                                            },
                                          },
                                          [
                                            a("font-awesome-icon", {
                                              attrs: { icon: "minus" },
                                            }),
                                          ],
                                          1,
                                        ),
                                        a("input", {
                                          directives: [
                                            {
                                              name: "model",
                                              rawName: "v-model.number",
                                              value: t.eraserHardness,
                                              expression: "eraserHardness",
                                              modifiers: { number: !0 },
                                            },
                                          ],
                                          staticClass:
                                            "browser-default pxt-input pxt-stepper-input",
                                          attrs: {
                                            type: "number",
                                            min: "0",
                                            max: "100",
                                          },
                                          domProps: { value: t.eraserHardness },
                                          on: {
                                            input: function (e) {
                                              e.target.composing ||
                                                (t.eraserHardness = t._n(
                                                  e.target.value,
                                                ));
                                            },
                                            blur: function (e) {
                                              return t.$forceUpdate();
                                            },
                                          },
                                        }),
                                        a(
                                          "button",
                                          {
                                            staticClass: "pxt-stepper-btn",
                                            attrs: { type: "button" },
                                            on: {
                                              click: function (e) {
                                                t.eraserHardness = Math.min(
                                                  100,
                                                  t.eraserHardness + 10,
                                                );
                                              },
                                            },
                                          },
                                          [
                                            a("font-awesome-icon", {
                                              attrs: { icon: "plus" },
                                            }),
                                          ],
                                          1,
                                        ),
                                        a(
                                          "span",
                                          { staticClass: "pxt-stepper-suffix" },
                                          [t._v("hardness")],
                                        ),
                                      ],
                                    ),
                                    a("p", { staticClass: "pxt-hint" }, [
                                      t._v(
                                        "\n                                Drag over the result above to erase. Lower hardness leaves a dithered,\n                                faded edge around the brush instead of a hard circle.\n                            ",
                                      ),
                                    ]),
                                  ],
                            ],
                            2,
                          )
                        : t._e(),
                      t.hasResult
                        ? a(
                            "button",
                            {
                              staticClass:
                                "pxt-btn pxt-btn--ghost pxt-btn--block pxt-btn--spaced",
                              attrs: { type: "button" },
                              on: { click: t.saveCurrentToCatalog },
                            },
                            [
                              a("font-awesome-icon", {
                                attrs: { icon: "save" },
                              }),
                              t._v(" Save to catalog\n                    "),
                            ],
                            1,
                          )
                        : t._e(),
                      t.hasResult && t.showDownload
                        ? a(
                            "button",
                            {
                              staticClass:
                                "pxt-btn pxt-btn--primary pxt-btn--block pxt-btn--spaced",
                              attrs: { type: "button" },
                              on: { click: t.downloadResult },
                            },
                            [
                              a("font-awesome-icon", {
                                attrs: { icon: "download" },
                              }),
                              t._v(" Download PNG\n                    "),
                            ],
                            1,
                          )
                        : t._e(),
                      t.hasResult && !t.showDownload
                        ? a(
                            "button",
                            {
                              staticClass:
                                "pxt-btn pxt-btn--primary pxt-btn--block pxt-btn--spaced",
                              attrs: { type: "button" },
                              on: { click: t.confirmResult },
                            },
                            [
                              a("font-awesome-icon", {
                                attrs: { icon: "check" },
                              }),
                              t._v(" Confirm\n                    "),
                            ],
                            1,
                          )
                        : t._e(),
                    ]),
                  ]),
                ]),
              ]),
              a("texture-catalog", {
                attrs: {
                  visible: t.catalogVisible,
                  "filter-width": t.outputWidth,
                  "filter-height": t.outputHeight,
                  "filter-colors": t.paletteColors,
                },
                on: {
                  close: function (e) {
                    t.catalogVisible = !1;
                  },
                  select: t.onCatalogSelect,
                },
              }),
            ],
            1,
          );
        },
        s = [
          function () {
            var t = this,
              e = t.$createElement,
              a = t._self._c || e;
            return a("p", { staticClass: "pxt-hint" }, [
              a("b", [t._v("Automatic")]),
              t._v(
                " uses Lanczos3 when shrinking (avoids aliasing/moiré) and nearest neighbor\n                        when\n                        enlarging (keeps hard pixel-art edges crisp instead of blurring them).\n                    ",
              ),
            ]);
          },
        ],
        r = (a("8e6e"), a("456d"), a("6c7b"), a("96cf"), a("c7c6"), a("bd86")),
        i = (a("7514"), a("c5f6"), a("768b")),
        o = (a("4f7f"), a("f9ab"), a("6aa2"), a("63d9"), a("75fc")),
        c = (a("55dd"), a("5df3"), a("f400"), a("3b8d")),
        l =
          (a("28a5"),
          a("ac4d"),
          a("8a81"),
          a("ac6a"),
          a("34ef"),
          a("9c29"),
          a("ecee")),
        u = a("c074"),
        d = a("2f62"),
        h = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a(
            "transition",
            {
              attrs: {
                "enter-active-class": "animated fadeIn faster",
                "leave-active-class": "animated fadeOut faster",
              },
            },
            [
              t.visible
                ? a(
                    "div",
                    { staticClass: "ptc-root" },
                    [
                      a("div", {
                        staticClass: "ptc-backdrop",
                        on: {
                          click: function (e) {
                            return t.$emit("close");
                          },
                        },
                      }),
                      a(
                        "transition",
                        {
                          attrs: {
                            appear: "",
                            "enter-active-class": "animated fadeInRight faster",
                            "leave-active-class":
                              "animated fadeOutRight faster",
                          },
                        },
                        [
                          a("aside", { staticClass: "ptc-panel" }, [
                            a("div", { staticClass: "ptc-header" }, [
                              a(
                                "h2",
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "images" },
                                  }),
                                  t._v(" Catalog"),
                                ],
                                1,
                              ),
                              a(
                                "button",
                                {
                                  staticClass: "ptc-close",
                                  attrs: { type: "button", title: "Close" },
                                  on: {
                                    click: function (e) {
                                      return t.$emit("close");
                                    },
                                  },
                                },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "times" },
                                  }),
                                ],
                                1,
                              ),
                            ]),
                            a("div", { staticClass: "ptc-toolbar" }, [
                              a(
                                "button",
                                {
                                  staticClass: "ptc-tool-btn",
                                  attrs: {
                                    type: "button",
                                    disabled:
                                      t.loading || 0 === t.entries.length,
                                  },
                                  on: { click: t.exportCatalog },
                                },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "file-export" },
                                  }),
                                  t._v(" Export all\n                    "),
                                ],
                                1,
                              ),
                              a(
                                "button",
                                {
                                  staticClass: "ptc-tool-btn",
                                  attrs: { type: "button" },
                                  on: {
                                    click: function (e) {
                                      return t.$refs.importInput.click();
                                    },
                                  },
                                },
                                [
                                  a("font-awesome-icon", {
                                    attrs: { icon: "file-import" },
                                  }),
                                  t._v(" Import\n                    "),
                                ],
                                1,
                              ),
                              a("input", {
                                ref: "importInput",
                                staticClass: "ptc-hidden-input",
                                attrs: {
                                  type: "file",
                                  accept: "application/json,.json",
                                },
                                on: { change: t.handleImportFile },
                              }),
                            ]),
                            t.pendingImport
                              ? a(
                                  "div",
                                  { staticClass: "ptc-import-confirm" },
                                  [
                                    a("p", [
                                      t._v(
                                        "Import " +
                                          t._s(t.pendingImport.length) +
                                          " image(s)?",
                                      ),
                                    ]),
                                    a(
                                      "div",
                                      { staticClass: "ptc-import-actions" },
                                      [
                                        a(
                                          "button",
                                          {
                                            staticClass: "ptc-import-merge",
                                            attrs: { type: "button" },
                                            on: {
                                              click: function (e) {
                                                return t.confirmImport("merge");
                                              },
                                            },
                                          },
                                          [
                                            t._v(
                                              "Merge\n                            (default)",
                                            ),
                                          ],
                                        ),
                                        a(
                                          "button",
                                          {
                                            staticClass: "ptc-import-replace",
                                            attrs: { type: "button" },
                                            on: {
                                              click: function (e) {
                                                return t.confirmImport(
                                                  "replace",
                                                );
                                              },
                                            },
                                          },
                                          [
                                            t._v(
                                              "Replace\n                            catalog",
                                            ),
                                          ],
                                        ),
                                        a(
                                          "button",
                                          {
                                            staticClass: "ptc-import-cancel",
                                            attrs: { type: "button" },
                                            on: {
                                              click: function (e) {
                                                t.pendingImport = null;
                                              },
                                            },
                                          },
                                          [t._v("Cancel")],
                                        ),
                                      ],
                                    ),
                                  ],
                                )
                              : t._e(),
                            t.hasFilter
                              ? a("p", { staticClass: "ptc-hint" }, [
                                  t._v(
                                    "\n                    Showing only images matching\n                    ",
                                  ),
                                  null != t.filterWidth &&
                                  null != t.filterHeight
                                    ? a("b", [
                                        t._v(
                                          t._s(t.filterWidth) +
                                            "×" +
                                            t._s(t.filterHeight) +
                                            "px",
                                        ),
                                      ])
                                    : t._e(),
                                  null != t.filterColors
                                    ? a("b", [
                                        t._v(t._s(t.filterColors) + " colors"),
                                      ])
                                    : t._e(),
                                  t._v(".\n                "),
                                ])
                              : t._e(),
                            t.loading
                              ? a(
                                  "div",
                                  { staticClass: "ptc-loading" },
                                  [
                                    a("font-awesome-icon", {
                                      attrs: { icon: "spinner", spin: "" },
                                    }),
                                    t._v(" Loading…"),
                                  ],
                                  1,
                                )
                              : 0 === t.filteredEntries.length
                                ? a(
                                    "div",
                                    { staticClass: "ptc-empty" },
                                    [
                                      a("font-awesome-icon", {
                                        staticClass: "ptc-empty-icon",
                                        attrs: { icon: "images" },
                                      }),
                                      a("p", [
                                        t._v(
                                          "No saved images " +
                                            t._s(
                                              t.hasFilter
                                                ? "match these settings"
                                                : "yet",
                                            ) +
                                            ".",
                                        ),
                                      ]),
                                      a("p", { staticClass: "ptc-empty-sub" }, [
                                        t._v(
                                          'Use "Save to catalog" in the editor to add images here.',
                                        ),
                                      ]),
                                    ],
                                    1,
                                  )
                                : a(
                                    "div",
                                    { staticClass: "ptc-grid" },
                                    t._l(t.filteredEntries, function (e) {
                                      return a(
                                        "div",
                                        { key: e.id, staticClass: "ptc-card" },
                                        [
                                          a(
                                            "div",
                                            {
                                              staticClass: "ptc-thumb",
                                              attrs: {
                                                title: "Use this image",
                                              },
                                              on: {
                                                click: function (a) {
                                                  return t.selectEntry(e);
                                                },
                                              },
                                            },
                                            [
                                              a("img", {
                                                attrs: {
                                                  src: e.objectUrl,
                                                  alt: e.width + "×" + e.height,
                                                },
                                              }),
                                            ],
                                          ),
                                          a(
                                            "div",
                                            { staticClass: "ptc-meta" },
                                            [
                                              a("span", [
                                                t._v(
                                                  t._s(e.width) +
                                                    "×" +
                                                    t._s(e.height) +
                                                    "px",
                                                ),
                                              ]),
                                              a("span", [
                                                t._v(
                                                  t._s(e.colors) + " colors",
                                                ),
                                              ]),
                                            ],
                                          ),
                                          a(
                                            "div",
                                            { staticClass: "ptc-date" },
                                            [
                                              t._v(
                                                t._s(t.formatDate(e.updatedAt)),
                                              ),
                                            ],
                                          ),
                                          t.confirmingId !== e.id
                                            ? a(
                                                "button",
                                                {
                                                  staticClass: "ptc-delete",
                                                  attrs: {
                                                    type: "button",
                                                    title: "Delete",
                                                  },
                                                  on: {
                                                    click: function (a) {
                                                      t.confirmingId = e.id;
                                                    },
                                                  },
                                                },
                                                [
                                                  a("font-awesome-icon", {
                                                    attrs: {
                                                      icon: "trash-alt",
                                                    },
                                                  }),
                                                ],
                                                1,
                                              )
                                            : a(
                                                "div",
                                                { staticClass: "ptc-confirm" },
                                                [
                                                  a("span", [t._v("Delete?")]),
                                                  a(
                                                    "button",
                                                    {
                                                      staticClass:
                                                        "ptc-confirm-yes",
                                                      attrs: { type: "button" },
                                                      on: {
                                                        click: function (a) {
                                                          return t.doDelete(
                                                            e.id,
                                                          );
                                                        },
                                                      },
                                                    },
                                                    [t._v("Yes")],
                                                  ),
                                                  a(
                                                    "button",
                                                    {
                                                      staticClass:
                                                        "ptc-confirm-no",
                                                      attrs: { type: "button" },
                                                      on: {
                                                        click: function (e) {
                                                          t.confirmingId = null;
                                                        },
                                                      },
                                                    },
                                                    [t._v("No")],
                                                  ),
                                                ],
                                              ),
                                        ],
                                      );
                                    }),
                                    0,
                                  ),
                          ]),
                        ],
                      ),
                    ],
                    1,
                  )
                : t._e(),
            ],
          );
        },
        p = [],
        f = (a("20d6"), "psx-texture-catalog"),
        m = 1,
        g = "images";
      function v() {
        return new Promise(function (t, e) {
          if (window.indexedDB) {
            var a = window.indexedDB.open(f, m);
            ((a.onupgradeneeded = function () {
              var t = a.result;
              t.objectStoreNames.contains(g) ||
                t.createObjectStore(g, { keyPath: "id" });
            }),
              (a.onsuccess = function () {
                return t(a.result);
              }),
              (a.onerror = function () {
                return e(
                  a.error || new Error("Failed to open catalog database"),
                );
              }));
          } else e(new Error("IndexedDB is not available in this browser"));
        });
      }
      function b(t) {
        return w.apply(this, arguments);
      }
      function w() {
        return (
          (w = Object(c["a"])(
            regeneratorRuntime.mark(function t(e) {
              var a;
              return regeneratorRuntime.wrap(function (t) {
                while (1)
                  switch ((t.prev = t.next)) {
                    case 0:
                      return ((t.next = 2), v());
                    case 2:
                      return (
                        (a = t.sent),
                        t.abrupt(
                          "return",
                          new Promise(function (t, n) {
                            var s = a.transaction(g, "readwrite");
                            (s.objectStore(g).put(e),
                              (s.oncomplete = function () {
                                (a.close(), t());
                              }),
                              (s.onerror = function () {
                                (a.close(), n(s.error));
                              }));
                          }),
                        )
                      );
                    case 4:
                    case "end":
                      return t.stop();
                  }
              }, t);
            }),
          )),
          w.apply(this, arguments)
        );
      }
      function y() {
        return x.apply(this, arguments);
      }
      function x() {
        return (
          (x = Object(c["a"])(
            regeneratorRuntime.mark(function t() {
              var e;
              return regeneratorRuntime.wrap(function (t) {
                while (1)
                  switch ((t.prev = t.next)) {
                    case 0:
                      return ((t.next = 2), v());
                    case 2:
                      return (
                        (e = t.sent),
                        t.abrupt(
                          "return",
                          new Promise(function (t, a) {
                            var n = e.transaction(g, "readonly"),
                              s = n.objectStore(g).getAll();
                            ((s.onsuccess = function () {
                              var a = (s.result || [])
                                .slice()
                                .sort(function (t, e) {
                                  return e.updatedAt - t.updatedAt;
                                });
                              (e.close(), t(a));
                            }),
                              (s.onerror = function () {
                                (e.close(), a(s.error));
                              }));
                          }),
                        )
                      );
                    case 4:
                    case "end":
                      return t.stop();
                  }
              }, t);
            }),
          )),
          x.apply(this, arguments)
        );
      }
      function C(t) {
        return _.apply(this, arguments);
      }
      function _() {
        return (
          (_ = Object(c["a"])(
            regeneratorRuntime.mark(function t(e) {
              var a;
              return regeneratorRuntime.wrap(function (t) {
                while (1)
                  switch ((t.prev = t.next)) {
                    case 0:
                      return ((t.next = 2), v());
                    case 2:
                      return (
                        (a = t.sent),
                        t.abrupt(
                          "return",
                          new Promise(function (t, n) {
                            var s = a.transaction(g, "readwrite");
                            (s.objectStore(g).delete(e),
                              (s.oncomplete = function () {
                                (a.close(), t());
                              }),
                              (s.onerror = function () {
                                (a.close(), n(s.error));
                              }));
                          }),
                        )
                      );
                    case 4:
                    case "end":
                      return t.stop();
                  }
              }, t);
            }),
          )),
          _.apply(this, arguments)
        );
      }
      function k() {
        return O.apply(this, arguments);
      }
      function O() {
        return (
          (O = Object(c["a"])(
            regeneratorRuntime.mark(function t() {
              var e;
              return regeneratorRuntime.wrap(function (t) {
                while (1)
                  switch ((t.prev = t.next)) {
                    case 0:
                      return ((t.next = 2), v());
                    case 2:
                      return (
                        (e = t.sent),
                        t.abrupt(
                          "return",
                          new Promise(function (t, a) {
                            var n = e.transaction(g, "readwrite");
                            (n.objectStore(g).clear(),
                              (n.oncomplete = function () {
                                (e.close(), t());
                              }),
                              (n.onerror = function () {
                                (e.close(), a(n.error));
                              }));
                          }),
                        )
                      );
                    case 4:
                    case "end":
                      return t.stop();
                  }
              }, t);
            }),
          )),
          O.apply(this, arguments)
        );
      }
      function S(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function M(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? S(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : S(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      l["c"].add(u["F"], u["cb"], u["U"], u["z"], u["A"]);
      var P = {
          name: "TextureCatalog",
          props: {
            visible: { type: Boolean, default: !1 },
            filterWidth: { type: Number, default: null },
            filterHeight: { type: Number, default: null },
            filterColors: { type: Number, default: null },
          },
          data: function () {
            return {
              entries: [],
              loading: !1,
              confirmingId: null,
              pendingImport: null,
            };
          },
          computed: {
            hasFilter: function () {
              return (
                null != this.filterWidth ||
                null != this.filterHeight ||
                null != this.filterColors
              );
            },
            filteredEntries: function () {
              var t = this;
              return this.hasFilter
                ? this.entries.filter(function (e) {
                    return (
                      (null == t.filterWidth || e.width === t.filterWidth) &&
                      (null == t.filterHeight || e.height === t.filterHeight) &&
                      (null == t.filterColors || e.colors === t.filterColors)
                    );
                  })
                : this.entries;
            },
          },
          watch: {
            visible: function (t) {
              t ? this.loadEntries() : this.cleanupObjectUrls();
            },
          },
          beforeDestroy: function () {
            this.cleanupObjectUrls();
          },
          methods: M({}, Object(d["b"])(["pushNotification"]), {
            notify: function (t, e) {
              "function" === typeof this.pushNotification
                ? this.pushNotification({ type: t, message: e })
                : console.log("[TextureCatalog]", t, e);
            },
            cleanupObjectUrls: function () {
              var t = !0,
                e = !1,
                a = void 0;
              try {
                for (
                  var n, s = this.entries[Symbol.iterator]();
                  !(t = (n = s.next()).done);
                  t = !0
                ) {
                  var r = n.value;
                  r.objectUrl && URL.revokeObjectURL(r.objectUrl);
                }
              } catch (i) {
                ((e = !0), (a = i));
              } finally {
                try {
                  t || null == s.return || s.return();
                } finally {
                  if (e) throw a;
                }
              }
            },
            loadEntries: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t() {
                  var e;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            return (
                              (this.loading = !0),
                              (this.confirmingId = null),
                              (t.prev = 2),
                              (t.next = 5),
                              y()
                            );
                          case 5:
                            ((e = t.sent),
                              this.cleanupObjectUrls(),
                              (this.entries = e.map(function (t) {
                                return M({}, t, {
                                  objectUrl: URL.createObjectURL(t.blob),
                                });
                              })),
                              (t.next = 14));
                            break;
                          case 10:
                            ((t.prev = 10),
                              (t.t0 = t["catch"](2)),
                              this.notify(
                                "danger",
                                "Could not load the catalog: " +
                                  (t.t0 && t.t0.message),
                              ),
                              (this.entries = []));
                          case 14:
                            return (
                              (t.prev = 14),
                              (this.loading = !1),
                              t.finish(14)
                            );
                          case 17:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                    [[2, 10, 14, 17]],
                  );
                }),
              );
              function e() {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            blobToDataUrl: function (t) {
              return new Promise(function (e, a) {
                var n = new FileReader();
                ((n.onload = function () {
                  return e(n.result);
                }),
                  (n.onerror = a),
                  n.readAsDataURL(t));
              });
            },
            selectEntry: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t(e) {
                  var a;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            return ((t.next = 2), this.blobToDataUrl(e.blob));
                          case 2:
                            ((a = t.sent), this.$emit("select", a));
                          case 4:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                  );
                }),
              );
              function e(e) {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            doDelete: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t(e) {
                  var a;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            return ((t.prev = 0), (t.next = 3), C(e));
                          case 3:
                            ((a = this.entries.findIndex(function (t) {
                              return t.id === e;
                            })),
                              -1 !== a &&
                                (URL.revokeObjectURL(this.entries[a].objectUrl),
                                this.entries.splice(a, 1)),
                              (t.next = 10));
                            break;
                          case 7:
                            ((t.prev = 7),
                              (t.t0 = t["catch"](0)),
                              this.notify(
                                "danger",
                                "Could not delete: " + (t.t0 && t.t0.message),
                              ));
                          case 10:
                            return (
                              (t.prev = 10),
                              (this.confirmingId = null),
                              t.finish(10)
                            );
                          case 13:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                    [[0, 7, 10, 13]],
                  );
                }),
              );
              function e(e) {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            formatDate: function (t) {
              try {
                return new Date(t).toLocaleString();
              } catch (e) {
                return "";
              }
            },
            exportCatalog: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t() {
                  var e,
                    a,
                    n,
                    s,
                    r,
                    i = this;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            if (0 !== this.entries.length) {
                              t.next = 3;
                              break;
                            }
                            return (
                              this.notify(
                                "info",
                                "Catalog is empty — nothing to export.",
                              ),
                              t.abrupt("return")
                            );
                          case 3:
                            return (
                              (t.prev = 3),
                              (t.next = 6),
                              Promise.all(
                                this.entries.map(
                                  (function () {
                                    var t = Object(c["a"])(
                                      regeneratorRuntime.mark(function t(e) {
                                        return regeneratorRuntime.wrap(
                                          function (t) {
                                            while (1)
                                              switch ((t.prev = t.next)) {
                                                case 0:
                                                  return (
                                                    (t.t0 = e.id),
                                                    (t.t1 = e.width),
                                                    (t.t2 = e.height),
                                                    (t.t3 = e.colors),
                                                    (t.t4 = e.updatedAt),
                                                    (t.next = 7),
                                                    i.blobToDataUrl(e.blob)
                                                  );
                                                case 7:
                                                  return (
                                                    (t.t5 = t.sent),
                                                    t.abrupt("return", {
                                                      id: t.t0,
                                                      width: t.t1,
                                                      height: t.t2,
                                                      colors: t.t3,
                                                      updatedAt: t.t4,
                                                      dataUrl: t.t5,
                                                    })
                                                  );
                                                case 9:
                                                case "end":
                                                  return t.stop();
                                              }
                                          },
                                          t,
                                        );
                                      }),
                                    );
                                    return function (e) {
                                      return t.apply(this, arguments);
                                    };
                                  })(),
                                ),
                              )
                            );
                          case 6:
                            ((e = t.sent),
                              (a = {
                                format: "psx-texture-catalog",
                                version: 1,
                                exportedAt: Date.now(),
                                entries: e,
                              }),
                              (n = new Blob([JSON.stringify(a)], {
                                type: "application/json",
                              })),
                              (s = URL.createObjectURL(n)),
                              (r = document.createElement("a")),
                              (r.href = s),
                              (r.download = "texture-catalog-export.json"),
                              document.body.appendChild(r),
                              r.click(),
                              document.body.removeChild(r),
                              URL.revokeObjectURL(s),
                              this.notify(
                                "success",
                                "Exported " + e.length + " image(s)",
                              ),
                              (t.next = 23));
                            break;
                          case 20:
                            ((t.prev = 20),
                              (t.t0 = t["catch"](3)),
                              this.notify(
                                "danger",
                                "Export failed: " + (t.t0 && t.t0.message),
                              ));
                          case 23:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                    [[3, 20]],
                  );
                }),
              );
              function e() {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            handleImportFile: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t(e) {
                  var a, n, s;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            if (
                              ((a = e.target.files && e.target.files[0]),
                              (e.target.value = ""),
                              a)
                            ) {
                              t.next = 4;
                              break;
                            }
                            return t.abrupt("return");
                          case 4:
                            return ((t.prev = 4), (t.next = 7), a.text());
                          case 7:
                            if (
                              ((n = t.sent),
                              (s = JSON.parse(n)),
                              s &&
                                "psx-texture-catalog" === s.format &&
                                Array.isArray(s.entries))
                            ) {
                              t.next = 12;
                              break;
                            }
                            return (
                              this.notify(
                                "danger",
                                "That file isn't a valid catalog export.",
                              ),
                              t.abrupt("return")
                            );
                          case 12:
                            if (0 !== s.entries.length) {
                              t.next = 15;
                              break;
                            }
                            return (
                              this.notify(
                                "info",
                                "That file has no images in it.",
                              ),
                              t.abrupt("return")
                            );
                          case 15:
                            ((this.pendingImport = s.entries), (t.next = 21));
                            break;
                          case 18:
                            ((t.prev = 18),
                              (t.t0 = t["catch"](4)),
                              this.notify(
                                "danger",
                                "Could not read that file: " +
                                  (t.t0 && t.t0.message),
                              ));
                          case 21:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                    [[4, 18]],
                  );
                }),
              );
              function e(e) {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            dataUrlToBlob: function (t) {
              return fetch(t).then(function (t) {
                return t.blob();
              });
            },
            confirmImport: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t(e) {
                  var a, n, s, r, i, o, c, l, u, d, h;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            if (
                              ((a = this.pendingImport),
                              (this.pendingImport = null),
                              a && 0 !== a.length)
                            ) {
                              t.next = 4;
                              break;
                            }
                            return t.abrupt("return");
                          case 4:
                            if (
                              ((this.loading = !0),
                              (t.prev = 5),
                              "replace" !== e)
                            ) {
                              t.next = 9;
                              break;
                            }
                            return ((t.next = 9), k());
                          case 9:
                            if (((t.t0 = Set), "merge" !== e)) {
                              t.next = 17;
                              break;
                            }
                            return ((t.next = 13), y());
                          case 13:
                            ((t.t2 = function (t) {
                              return t.id;
                            }),
                              (t.t1 = t.sent.map(t.t2)),
                              (t.next = 18));
                            break;
                          case 17:
                            t.t1 = [];
                          case 18:
                            ((t.t3 = t.t1),
                              (n = new t.t0(t.t3)),
                              (s = 0),
                              (r = !0),
                              (i = !1),
                              (o = void 0),
                              (t.prev = 24),
                              (c = a[Symbol.iterator]()));
                          case 26:
                            if ((r = (l = c.next()).done)) {
                              t.next = 40;
                              break;
                            }
                            return (
                              (u = l.value),
                              (t.next = 30),
                              this.dataUrlToBlob(u.dataUrl)
                            );
                          case 30:
                            ((d = t.sent), (h = u.id));
                            while (n.has(h)) h += 1;
                            return (
                              n.add(h),
                              (t.next = 36),
                              b({
                                id: h,
                                blob: d,
                                width: u.width,
                                height: u.height,
                                colors: u.colors,
                                updatedAt: u.updatedAt || Date.now(),
                              })
                            );
                          case 36:
                            s++;
                          case 37:
                            ((r = !0), (t.next = 26));
                            break;
                          case 40:
                            t.next = 46;
                            break;
                          case 42:
                            ((t.prev = 42),
                              (t.t4 = t["catch"](24)),
                              (i = !0),
                              (o = t.t4));
                          case 46:
                            ((t.prev = 46),
                              (t.prev = 47),
                              r || null == c.return || c.return());
                          case 49:
                            if (((t.prev = 49), !i)) {
                              t.next = 52;
                              break;
                            }
                            throw o;
                          case 52:
                            return t.finish(49);
                          case 53:
                            return t.finish(46);
                          case 54:
                            return (
                              this.notify(
                                "success",
                                ("replace" === e
                                  ? "Replaced catalog with "
                                  : "Merged ") +
                                  s +
                                  " image(s)",
                              ),
                              (t.next = 57),
                              this.loadEntries()
                            );
                          case 57:
                            t.next = 63;
                            break;
                          case 59:
                            ((t.prev = 59),
                              (t.t5 = t["catch"](5)),
                              this.notify(
                                "danger",
                                "Import failed: " + (t.t5 && t.t5.message),
                              ),
                              (this.loading = !1));
                          case 63:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                    [
                      [5, 59],
                      [24, 42, 46, 54],
                      [47, , 49, 53],
                    ],
                  );
                }),
              );
              function e(e) {
                return t.apply(this, arguments);
              }
              return e;
            })(),
          }),
        },
        E = P,
        I = (a("1082"), a("2877")),
        L = Object(I["a"])(E, h, p, !1, null, "a28dda3a", null),
        D = L.exports;
      function R(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function j(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? R(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : R(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      l["c"].add(
        u["t"],
        u["gb"],
        u["I"],
        u["y"],
        u["m"],
        u["M"],
        u["K"],
        u["J"],
        u["r"],
        u["D"],
        u["u"],
        u["U"],
        u["H"],
        u["V"],
        u["db"],
        u["v"],
        u["F"],
        u["P"],
        u["E"],
        u["O"],
        u["o"],
      );
      var T = (function () {
        for (var t = new Uint32Array(256), e = 0; e < 256; e++) {
          for (var a = e, n = 0; n < 8; n++)
            a = 1 & a ? 3988292384 ^ (a >>> 1) : a >>> 1;
          t[e] = a >>> 0;
        }
        return t;
      })();
      function A(t) {
        for (var e = 4294967295, a = 0; a < t.length; a++)
          e = T[255 & (e ^ t[a])] ^ (e >>> 8);
        return (4294967295 ^ e) >>> 0;
      }
      function U(t) {
        return new Uint8Array([
          (t >>> 24) & 255,
          (t >>> 16) & 255,
          (t >>> 8) & 255,
          255 & t,
        ]);
      }
      function N(t) {
        var e = 0,
          a = !0,
          n = !1,
          s = void 0;
        try {
          for (
            var r, i = t[Symbol.iterator]();
            !(a = (r = i.next()).done);
            a = !0
          ) {
            var o = r.value;
            e += o.length;
          }
        } catch (g) {
          ((n = !0), (s = g));
        } finally {
          try {
            a || null == i.return || i.return();
          } finally {
            if (n) throw s;
          }
        }
        var c = new Uint8Array(e),
          l = 0,
          u = !0,
          d = !1,
          h = void 0;
        try {
          for (
            var p, f = t[Symbol.iterator]();
            !(u = (p = f.next()).done);
            u = !0
          ) {
            var m = p.value;
            (c.set(m, l), (l += m.length));
          }
        } catch (g) {
          ((d = !0), (h = g));
        } finally {
          try {
            u || null == f.return || f.return();
          } finally {
            if (d) throw h;
          }
        }
        return c;
      }
      function z(t, e) {
        var a = new Uint8Array(
            t.split("").map(function (t) {
              return t.charCodeAt(0);
            }),
          ),
          n = N([a, e]);
        return N([U(e.length), n, U(A(n))]);
      }
      function F(t) {
        return H.apply(this, arguments);
      }
      function H() {
        return (
          (H = Object(c["a"])(
            regeneratorRuntime.mark(function t(e) {
              var a, n, s;
              return regeneratorRuntime.wrap(function (t) {
                while (1)
                  switch ((t.prev = t.next)) {
                    case 0:
                      return (
                        (a = new CompressionStream("deflate")),
                        (n = a.writable.getWriter()),
                        n.write(e),
                        n.close(),
                        (t.next = 6),
                        new Response(a.readable).arrayBuffer()
                      );
                    case 6:
                      return (
                        (s = t.sent),
                        t.abrupt("return", new Uint8Array(s))
                      );
                    case 8:
                    case "end":
                      return t.stop();
                  }
              }, t);
            }),
          )),
          H.apply(this, arguments)
        );
      }
      function $(t) {
        return t <= 2 ? 1 : t <= 4 ? 2 : t <= 16 ? 4 : 8;
      }
      function B(t, e, a, n, s) {
        return W.apply(this, arguments);
      }
      function W() {
        return (
          (W = Object(c["a"])(
            regeneratorRuntime.mark(function t(e, a, n, s, r) {
              var i, o, c, l, u, d, h, p, f, m, g, v, b, w, y, x, C, _, k;
              return regeneratorRuntime.wrap(function (t) {
                while (1)
                  switch ((t.prev = t.next)) {
                    case 0:
                      for (
                        i = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]),
                          o = $(s.length),
                          c = z(
                            "IHDR",
                            N([U(e), U(a), new Uint8Array([o, 3, 0, 0, 0])]),
                          ),
                          l = new Uint8Array(3 * s.length),
                          u = 0;
                        u < s.length;
                        u++
                      )
                        ((l[3 * u] = s[u][0]),
                          (l[3 * u + 1] = s[u][1]),
                          (l[3 * u + 2] = s[u][2]));
                      for (
                        d = z("PLTE", l),
                          h = new Uint8Array(0),
                          null !== r &&
                            void 0 !== r &&
                            ((p = new Uint8Array(r + 1).fill(255)),
                            (p[r] = 0),
                            (h = z("tRNS", p))),
                          f = Math.ceil((e * o) / 8),
                          m = new Uint8Array((f + 1) * a),
                          g = 0,
                          v = 0;
                        v < a;
                        v++
                      )
                        if (((m[g++] = 0), 8 === o))
                          for (b = 0; b < e; b++) m[g++] = n[v * e + b];
                        else {
                          for (w = 0, y = 0, x = 0; x < e; x++) {
                            ((w = (w << o) | n[v * e + x]), (y += o));
                            while (y >= 8)
                              ((y -= 8), (m[g++] = (w >> y) & 255));
                          }
                          y > 0 && (m[g++] = (w << (8 - y)) & 255);
                        }
                      return ((t.next = 14), F(m));
                    case 14:
                      return (
                        (C = t.sent),
                        (_ = z("IDAT", C)),
                        (k = z("IEND", new Uint8Array(0))),
                        t.abrupt("return", N([i, c, d, h, _, k]))
                      );
                    case 18:
                    case "end":
                      return t.stop();
                  }
              }, t);
            }),
          )),
          W.apply(this, arguments)
        );
      }
      function Y(t) {
        return Math.abs(t) <= 0.5 ? 1 : 0;
      }
      function q(t) {
        return ((t = Math.abs(t)), t < 1 ? 1 - t : 0);
      }
      function X(t) {
        return (
          (t = Math.abs(t)),
          t < 1
            ? 1.5 * t * t * t - 2.5 * t * t + 1
            : t < 2
              ? -0.5 * t * t * t + 2.5 * t * t - 4 * t + 2
              : 0
        );
      }
      function G(t) {
        if (0 === t) return 1;
        var e = Math.PI * t;
        return Math.sin(e) / e;
      }
      function Z(t) {
        return ((t = Math.abs(t)), t < 3 ? G(t) * G(t / 3) : 0);
      }
      function V(t) {
        return ((t = Math.abs(t)), t < 2 ? G(t) * G(t / 2) : 0);
      }
      function K(t) {
        t = Math.abs(t);
        var e = 1 / 3,
          a = 1 / 3;
        return t < 1
          ? ((12 - 9 * e - 6 * a) * Math.pow(t, 3) +
              (12 * e - 18 + 6 * a) * Math.pow(t, 2) +
              (6 - 2 * e)) /
              6
          : t < 2
            ? ((-e - 6 * a) * Math.pow(t, 3) +
                (6 * e + 30 * a) * Math.pow(t, 2) +
                (-12 * e - 48 * a) * t +
                (8 * e + 24 * a)) /
              6
            : 0;
      }
      function J(t) {
        var e = 0.8;
        return Math.exp((-t * t) / (2 * e * e));
      }
      var Q = {
        box: { fn: Y, radius: 0.5 },
        triangle: { fn: q, radius: 1 },
        catmullrom: { fn: X, radius: 2 },
        mitchell: { fn: K, radius: 2 },
        lanczos2: { fn: V, radius: 2 },
        lanczos3: { fn: Z, radius: 3 },
        gaussian: { fn: J, radius: 2.5 },
      };
      function tt(t, e, a) {
        for (
          var n = Q[a],
            s = e / t,
            r = s < 1 ? 1 / s : 1,
            i = n.radius * r,
            c = [],
            l = function (e) {
              for (
                var a = (e + 0.5) / s,
                  l = Math.floor(a - i),
                  u = Math.ceil(a + i),
                  d = new Map(),
                  h = 0,
                  p = l;
                p <= u;
                p++
              ) {
                var f = n.fn((p + 0.5 - a) / r);
                if (0 !== f) {
                  var m = Math.min(Math.max(p, 0), t - 1);
                  (d.set(m, (d.get(m) || 0) + f), (h += f));
                }
              }
              var g = Object(o["a"])(d.keys()).sort(function (t, e) {
                  return t - e;
                }),
                v = g.map(function (t) {
                  return d.get(t) / h;
                });
              c.push({ idxs: g, weights: v });
            },
            u = 0;
          u < e;
          u++
        )
          l(u);
        return c;
      }
      function et(t, e, a, n, s) {
        var r = n.length,
          i = s ? r : e,
          o = s ? a : r,
          c = new Float32Array(i * o * 4);
        if (s)
          for (var l = 0; l < a; l++)
            for (var u = 0; u < r; u++) {
              for (
                var d = n[u],
                  h = d.idxs,
                  p = d.weights,
                  f = 0,
                  m = 0,
                  g = 0,
                  v = 0,
                  b = 0;
                b < h.length;
                b++
              ) {
                var w = 4 * (l * e + h[b]),
                  y = p[b];
                ((f += t[w] * y),
                  (m += t[w + 1] * y),
                  (g += t[w + 2] * y),
                  (v += t[w + 3] * y));
              }
              var x = 4 * (l * i + u);
              ((c[x] = f), (c[x + 1] = m), (c[x + 2] = g), (c[x + 3] = v));
            }
        else
          for (var C = 0; C < r; C++)
            for (
              var _ = n[C], k = ((h = _.idxs), (p = _.weights), 0);
              k < e;
              k++
            ) {
              for (var O = 0, S = 0, M = 0, P = 0, E = 0; E < h.length; E++) {
                var I = 4 * (h[E] * e + k),
                  L = p[E];
                ((O += t[I] * L),
                  (S += t[I + 1] * L),
                  (M += t[I + 2] * L),
                  (P += t[I + 3] * L));
              }
              var D = 4 * (C * i + k);
              ((c[D] = O), (c[D + 1] = S), (c[D + 2] = M), (c[D + 3] = P));
            }
        return c;
      }
      function at(t, e, a, n, s, r) {
        for (var i = new Float32Array(e * a * 4), o = 0; o < e * a; o++) {
          var c = t[4 * o + 3] / 255;
          ((i[4 * o] = t[4 * o] * c),
            (i[4 * o + 1] = t[4 * o + 1] * c),
            (i[4 * o + 2] = t[4 * o + 2] * c),
            (i[4 * o + 3] = t[4 * o + 3]));
        }
        for (
          var l = tt(e, n, r),
            u = et(i, e, a, l, !0),
            d = tt(a, s, r),
            h = et(u, n, a, d, !1),
            p = new Uint8ClampedArray(n * s * 4),
            f = 0;
          f < n * s;
          f++
        ) {
          var m = h[4 * f + 3];
          if (m <= 1e-4)
            ((p[4 * f] = 0),
              (p[4 * f + 1] = 0),
              (p[4 * f + 2] = 0),
              (p[4 * f + 3] = 0));
          else {
            var g = m / 255;
            ((p[4 * f] = h[4 * f] / g),
              (p[4 * f + 1] = h[4 * f + 1] / g),
              (p[4 * f + 2] = h[4 * f + 2] / g),
              (p[4 * f + 3] = m));
          }
        }
        return p;
      }
      function nt(t, e, a, n, s) {
        for (var r = new Uint8ClampedArray(n * s * 4), i = 0; i < s; i++)
          for (
            var o = Math.min(a - 1, Math.floor(((i + 0.5) * a) / s)), c = 0;
            c < n;
            c++
          ) {
            var l = Math.min(e - 1, Math.floor(((c + 0.5) * e) / n)),
              u = 4 * (o * e + l),
              d = 4 * (i * n + c);
            ((r[d] = t[u]),
              (r[d + 1] = t[u + 1]),
              (r[d + 2] = t[u + 2]),
              (r[d + 3] = t[u + 3]));
          }
        return r;
      }
      function st(t, e) {
        for (var a = [], n = 0, s = -e; s <= e; s++) {
          var r = Math.exp((-s * s) / (2 * t * t));
          (a.push(r), (n += r));
        }
        return a.map(function (t) {
          return t / n;
        });
      }
      function rt(t, e, a, n) {
        if (!n || n <= 0) return t;
        for (
          var s = Math.max(1, Math.ceil(2 * n)),
            r = st(n, s),
            i = new Float32Array(e * a * 4),
            o = 0;
          o < e * a;
          o++
        ) {
          var c = t[4 * o + 3] / 255;
          ((i[4 * o] = t[4 * o] * c),
            (i[4 * o + 1] = t[4 * o + 1] * c),
            (i[4 * o + 2] = t[4 * o + 2] * c),
            (i[4 * o + 3] = t[4 * o + 3]));
        }
        for (var l = new Float32Array(e * a * 4), u = 0; u < a; u++)
          for (var d = 0; d < e; d++) {
            for (var h = 0, p = 0, f = 0, m = 0, g = -s; g <= s; g++) {
              var v = Math.min(e - 1, Math.max(0, d + g)),
                b = r[g + s],
                w = 4 * (u * e + v);
              ((h += i[w] * b),
                (p += i[w + 1] * b),
                (f += i[w + 2] * b),
                (m += i[w + 3] * b));
            }
            var y = 4 * (u * e + d);
            ((l[y] = h), (l[y + 1] = p), (l[y + 2] = f), (l[y + 3] = m));
          }
        for (var x = new Float32Array(e * a * 4), C = 0; C < a; C++)
          for (var _ = 0; _ < e; _++) {
            for (var k = 0, O = 0, S = 0, M = 0, P = -s; P <= s; P++) {
              var E = Math.min(a - 1, Math.max(0, C + P)),
                I = r[P + s],
                L = 4 * (E * e + _);
              ((k += l[L] * I),
                (O += l[L + 1] * I),
                (S += l[L + 2] * I),
                (M += l[L + 3] * I));
            }
            var D = 4 * (C * e + _);
            ((x[D] = k), (x[D + 1] = O), (x[D + 2] = S), (x[D + 3] = M));
          }
        for (var R = new Uint8ClampedArray(e * a * 4), j = 0; j < e * a; j++) {
          var T = x[4 * j + 3];
          if (T <= 1e-4)
            ((R[4 * j] = 0),
              (R[4 * j + 1] = 0),
              (R[4 * j + 2] = 0),
              (R[4 * j + 3] = 0));
          else {
            var A = T / 255;
            ((R[4 * j] = x[4 * j] / A),
              (R[4 * j + 1] = x[4 * j + 1] / A),
              (R[4 * j + 2] = x[4 * j + 2] / A),
              (R[4 * j + 3] = T));
          }
        }
        return R;
      }
      var it = [0, 0.4, 0.8, 1.3];
      function ot(t, e) {
        for (var a = new Map(), n = !1, s = 0; s < e; s++) {
          var r = t[4 * s + 3];
          if (r < 128) n = !0;
          else {
            var i = t[4 * s],
              c = t[4 * s + 1],
              l = t[4 * s + 2],
              u = (i << 16) | (c << 8) | l,
              d = a.get(u);
            d ? d.count++ : a.set(u, { r: i, g: c, b: l, count: 1 });
          }
        }
        var h = Object(o["a"])(a.values()),
          p = 2e4;
        if (h.length > p) {
          for (var f = h.length / p, m = [], g = 0; g < p; g++)
            m.push(h[Math.floor(g * f)]);
          h = m;
        }
        return { items: h, hasTransparency: n };
      }
      function ct(t, e) {
        if (0 === t.length) return [[0, 0, 0]];
        if (t.length <= e)
          return t.map(function (t) {
            return [t.r, t.g, t.b];
          });
        var a = [{ items: t.slice() }];
        function n(t) {
          var e = 255,
            a = 0,
            n = 255,
            s = 0,
            r = 255,
            i = 0,
            o = !0,
            c = !1,
            l = void 0;
          try {
            for (
              var u, d = t[Symbol.iterator]();
              !(o = (u = d.next()).done);
              o = !0
            ) {
              var h = u.value;
              (h.r < e && (e = h.r),
                h.r > a && (a = h.r),
                h.g < n && (n = h.g),
                h.g > s && (s = h.g),
                h.b < r && (r = h.b),
                h.b > i && (i = h.b));
            }
          } catch (g) {
            ((c = !0), (l = g));
          } finally {
            try {
              o || null == d.return || d.return();
            } finally {
              if (c) throw l;
            }
          }
          var p = a - e,
            f = s - n,
            m = i - r;
          return p >= f && p >= m ? "r" : f >= p && f >= m ? "g" : "b";
        }
        var s = function () {
          for (var t = -1, e = -1, s = 0; s < a.length; s++)
            a[s].items.length > 1 &&
              a[s].items.length > e &&
              ((e = a[s].items.length), (t = s));
          if (-1 === t) return "break";
          var r = a[t],
            i = n(r.items);
          r.items.sort(function (t, e) {
            return t[i] - e[i];
          });
          for (
            var o = r.items.reduce(function (t, e) {
                return t + e.count;
              }, 0),
              c = 0,
              l = 0,
              u = 0;
            u < r.items.length;
            u++
          )
            if (((c += r.items[u].count), c >= o / 2)) {
              l = u + 1;
              break;
            }
          (l <= 0 && (l = 1),
            l >= r.items.length && (l = r.items.length - 1),
            a.splice(
              t,
              1,
              { items: r.items.slice(0, l) },
              { items: r.items.slice(l) },
            ));
        };
        while (a.length < e) {
          var r = s();
          if ("break" === r) break;
        }
        return a.map(function (t) {
          var e = 0,
            a = 0,
            n = 0,
            s = 0,
            r = !0,
            i = !1,
            o = void 0;
          try {
            for (
              var c, l = t.items[Symbol.iterator]();
              !(r = (c = l.next()).done);
              r = !0
            ) {
              var u = c.value;
              ((e += u.r * u.count),
                (a += u.g * u.count),
                (n += u.b * u.count),
                (s += u.count));
            }
          } catch (d) {
            ((i = !0), (o = d));
          } finally {
            try {
              r || null == l.return || l.return();
            } finally {
              if (i) throw o;
            }
          }
          return [Math.round(e / s), Math.round(a / s), Math.round(n / s)];
        });
      }
      function lt(t, e, a) {
        for (
          var n = e.map(function (t) {
              return Object(o["a"])(t);
            }),
            s = function (e) {
              var a = n.map(function () {
                  return [0, 0, 0, 0];
                }),
                s = !0,
                r = !1,
                i = void 0;
              try {
                for (
                  var o, c = t[Symbol.iterator]();
                  !(s = (o = c.next()).done);
                  s = !0
                ) {
                  for (
                    var l = o.value, u = 0, d = 1 / 0, h = 0;
                    h < n.length;
                    h++
                  ) {
                    var p = n[h],
                      f =
                        Math.pow(l.r - p[0], 2) +
                        Math.pow(l.g - p[1], 2) +
                        Math.pow(l.b - p[2], 2);
                    f < d && ((d = f), (u = h));
                  }
                  ((a[u][0] += l.r * l.count),
                    (a[u][1] += l.g * l.count),
                    (a[u][2] += l.b * l.count),
                    (a[u][3] += l.count));
                }
              } catch (m) {
                ((r = !0), (i = m));
              } finally {
                try {
                  s || null == c.return || c.return();
                } finally {
                  if (r) throw i;
                }
              }
              n = n.map(function (t, e) {
                return a[e][3] > 0
                  ? [
                      Math.round(a[e][0] / a[e][3]),
                      Math.round(a[e][1] / a[e][3]),
                      Math.round(a[e][2] / a[e][3]),
                    ]
                  : t;
              });
            },
            r = 0;
          r < a;
          r++
        )
          s(r);
        return n;
      }
      function ut(t, e, a, n, s) {
        for (var r = s, i = 1 / 0, o = 0; o < n.length; o++) {
          var c = n[o],
            l =
              Math.pow(t - c[0], 2) +
              Math.pow(e - c[1], 2) +
              Math.pow(a - c[2], 2);
          l < i && ((i = l), (r = o + s));
        }
        return r;
      }
      var dt = [
        [0, 8, 2, 10],
        [12, 4, 14, 6],
        [3, 11, 1, 9],
        [15, 7, 13, 5],
      ];
      function ht(t, e, a, n, s) {
        var r = ot(t, e * a),
          i = r.items,
          c = r.hasTransparency,
          l = c ? Math.max(1, n - 1) : n,
          u = ct(i, l);
        i.length > u.length && (u = lt(i, u, 5));
        var d = c ? [[255, 0, 255]].concat(Object(o["a"])(u)) : u,
          h = c ? 1 : 0,
          p = c ? 0 : null,
          f = new Uint8Array(e * a);
        if ("none" === s)
          for (var m = 0; m < e * a; m++) {
            var g = t[4 * m + 3];
            f[m] =
              c && g < 128 ? 0 : ut(t[4 * m], t[4 * m + 1], t[4 * m + 2], u, h);
          }
        else if ("floyd" === s)
          (function () {
            for (var n = new Float32Array(e * a * 3), s = 0; s < e * a; s++)
              ((n[3 * s] = t[4 * s]),
                (n[3 * s + 1] = t[4 * s + 1]),
                (n[3 * s + 2] = t[4 * s + 2]));
            for (
              var r = function (e) {
                  return !c || t[4 * e + 3] >= 128;
                },
                i = 0;
              i < a;
              i++
            )
              for (
                var o = function (t) {
                    var s = i * e + t;
                    if (!r(s)) return ((f[s] = 0), "continue");
                    var o = Math.min(255, Math.max(0, n[3 * s])),
                      c = Math.min(255, Math.max(0, n[3 * s + 1])),
                      l = Math.min(255, Math.max(0, n[3 * s + 2])),
                      p = ut(o, c, l, u, h);
                    f[s] = p;
                    var m = d[p],
                      g = o - m[0],
                      v = c - m[1],
                      b = l - m[2],
                      w = function (t, s, i) {
                        if (!(t < 0 || t >= e || s < 0 || s >= a)) {
                          var o = s * e + t;
                          r(o) &&
                            ((n[3 * o] = Math.min(
                              255,
                              Math.max(0, n[3 * o] + g * i),
                            )),
                            (n[3 * o + 1] = Math.min(
                              255,
                              Math.max(0, n[3 * o + 1] + v * i),
                            )),
                            (n[3 * o + 2] = Math.min(
                              255,
                              Math.max(0, n[3 * o + 2] + b * i),
                            )));
                        }
                      };
                    (w(t + 1, i, 7 / 16),
                      w(t - 1, i + 1, 3 / 16),
                      w(t, i + 1, 5 / 16),
                      w(t + 1, i + 1, 1 / 16));
                  },
                  l = 0;
                l < e;
                l++
              )
                o(l);
          })();
        else
          for (
            var v = 255 / Math.cbrt(Math.max(2, u.length)), b = 0;
            b < a;
            b++
          )
            for (var w = 0; w < e; w++) {
              var y = b * e + w,
                x = t[4 * y + 3];
              if (c && x < 128) f[y] = 0;
              else {
                var C = (dt[3 & b][3 & w] / 16 - 0.5) * v,
                  _ = Math.min(255, Math.max(0, t[4 * y] + C)),
                  k = Math.min(255, Math.max(0, t[4 * y + 1] + C)),
                  O = Math.min(255, Math.max(0, t[4 * y + 2] + C));
                f[y] = ut(_, k, O, u, h);
              }
            }
        return {
          indices: f,
          palette: d,
          transparentIndex: p,
          hasTransparency: c,
        };
      }
      function pt(t, e) {
        return Math.sqrt(
          Math.pow(t[0] - e[0], 2) +
            Math.pow(t[1] - e[1], 2) +
            Math.pow(t[2] - e[2], 2),
        );
      }
      var ft = Math.sqrt(195075);
      function mt(t) {
        for (var e = -1, a = -1, n = 1 / 0, s = 0; s < t.length; s++)
          for (var r = s + 1; r < t.length; r++) {
            var i = pt(t[s], t[r]);
            i < n && ((n = i), (e = s), (a = r));
          }
        return { i: e, j: a };
      }
      function gt(t, e) {
        if (e.length < 2) return null;
        for (
          var a = mt(e), n = a.i, s = a.j, r = new Uint8Array(t.length), i = 0;
          i < t.length;
          i++
        )
          r[i] = t[i] === s ? n : t[i];
        var o = e.map(function (t, e) {
          return e === s ? [255, 0, 255] : t;
        });
        return { indices: r, palette: o, transparentIndex: s };
      }
      function vt(t, e, a, n, s) {
        for (
          var r = (s / 100) * ft, i = e[n], o = new Set(), c = 0;
          c < e.length;
          c++
        )
          c !== a && pt(e[c], i) <= r && o.add(c);
        if (0 === o.size)
          return { indices: t, palette: e, transparentIndex: a, changed: 0 };
        var l = a,
          u = e;
        (null !== l && void 0 !== l) ||
          ((l = n),
          (u = e.map(function (t, e) {
            return e === l ? [255, 0, 255] : t;
          })));
        for (var d = new Uint8Array(t.length), h = 0, p = 0; p < t.length; p++)
          o.has(t[p]) ? ((d[p] = l), h++) : (d[p] = t[p]);
        return { indices: d, palette: u, transparentIndex: l, changed: h };
      }
      function bt(t, e, a, n, s, r, c, l) {
        var u = t,
          d = e,
          h = s,
          p = !1;
        if (null === h || void 0 === h)
          if (d.length < 256)
            ((d = [].concat(Object(o["a"])(d), [[255, 0, 255]])),
              (h = d.length - 1));
          else {
            var f = gt(u, d);
            if (!f) return null;
            ((u = f.indices),
              (d = f.palette),
              (h = f.transparentIndex),
              (p = !0));
          }
        var m = u[c * a + r];
        if (m === h) return null;
        var g = d[m],
          v = (l / 100) * ft,
          b = new Uint8Array(a * n),
          w = [c * a + r];
        b[c * a + r] = 1;
        var y = [];
        while (w.length) {
          var x = w.pop();
          y.push(x);
          for (
            var C = x % a,
              _ = (x / a) | 0,
              k = [
                [C - 1, _],
                [C + 1, _],
                [C, _ - 1],
                [C, _ + 1],
              ],
              O = 0,
              S = k;
            O < S.length;
            O++
          ) {
            var M = Object(i["a"])(S[O], 2),
              P = M[0],
              E = M[1];
            if (!(P < 0 || P >= a || E < 0 || E >= n)) {
              var I = E * a + P;
              if (!b[I]) {
                var L = u[I];
                L !== h && pt(d[L], g) <= v && ((b[I] = 1), w.push(I));
              }
            }
          }
        }
        for (var D = new Uint8Array(u), R = 0, j = y; R < j.length; R++) {
          var T = j[R];
          D[T] = h;
        }
        return {
          indices: D,
          palette: d,
          transparentIndex: h,
          changed: y.length,
          reindexed: p,
        };
      }
      function wt(t, e, a, n, s, r, i, c, l) {
        var u = s,
          d = e,
          h = t,
          p = !1;
        if (null === u || void 0 === u)
          if (d.length < 256)
            ((d = [].concat(Object(o["a"])(d), [[255, 0, 255]])),
              (u = d.length - 1));
          else {
            var f = gt(h, d);
            if (!f)
              return {
                indices: h,
                palette: d,
                transparentIndex: null,
                changed: 0,
                reindexed: !1,
              };
            ((h = f.indices),
              (d = f.palette),
              (u = f.transparentIndex),
              (p = !0));
          }
        for (
          var m = c * (l / 100),
            g = Math.max(0, Math.floor(r - c)),
            v = Math.min(a - 1, Math.ceil(r + c)),
            b = Math.max(0, Math.floor(i - c)),
            w = Math.min(n - 1, Math.ceil(i + c)),
            y = 0,
            x = b;
          x <= w;
          x++
        )
          for (var C = g; C <= v; C++) {
            var _ = C + 0.5 - r,
              k = x + 0.5 - i,
              O = Math.sqrt(_ * _ + k * k);
            if (!(O > c)) {
              var S = x * a + C;
              if (h[S] !== u) {
                var M = void 0;
                ((M =
                  m >= c ||
                  O <= m ||
                  1 - (O - m) / (c - m) > dt[3 & x][3 & C] / 16),
                  M && ((h[S] = u), y++));
              }
            }
          }
        return {
          indices: h,
          palette: d,
          transparentIndex: u,
          changed: y,
          reindexed: p,
        };
      }
      var yt = {
          name: "TextureIndexer",
          components: { TextureCatalog: D },
          props: {
            imageData: { type: String, default: null },
            showDownload: { type: Boolean, default: !0 },
            outputWidth: { type: Number, default: null },
            outputHeight: { type: Number, default: null },
            paletteColors: { type: Number, default: null },
          },
          data: function () {
            return {
              hasImage: !1,
              catalogVisible: !1,
              srcW: 0,
              srcH: 0,
              displayScale: 1,
              zoomSteps: [1, 1.5, 2, 3, 4, 6, 8],
              zoomIndex: 0,
              zoomLevel: 1,
              interactionMode: "select",
              resultZoomSteps: [1, 1.5, 2, 3, 4, 6, 8],
              resultZoomIndex: 0,
              resultZoomLevel: 1,
              resultInteractionMode: "select",
              dragState: null,
              isDraggingFile: !1,
              crop: { x: 0, y: 0, w: 0, h: 0 },
              cropMode: "free",
              widthLocal: null != this.outputWidth ? this.outputWidth : 64,
              heightLocal: null != this.outputHeight ? this.outputHeight : 64,
              colorsLocal: null != this.paletteColors ? this.paletteColors : 16,
              resizeAlgo: "auto",
              edgeSmoothing: 0,
              ditherMode: "none",
              bgRemovalMode: "color",
              bgTolerance: 15,
              eraserSize: 3,
              eraserHardness: 60,
              undoStackSize: 0,
              isProcessing: !1,
              hasResult: !1,
              resultDims: "",
              resultPalette: [],
              resultTransparentIndex: null,
              resultStatus: "",
              resultDataUrl: null,
              resizeAlgoOptions: [
                { value: "auto", title: "Automatic", desc: "recommended" },
                {
                  value: "nearest",
                  title: "Nearest neighbor",
                  desc: "keeps hard pixel edges",
                },
                {
                  value: "lanczos3",
                  title: "Lanczos3",
                  desc: "sharpest, some ringing on hard edges",
                },
                {
                  value: "lanczos2",
                  title: "Lanczos2",
                  desc: "sharp, less ringing than Lanczos3",
                },
                {
                  value: "mitchell",
                  title: "Mitchell-Netravali",
                  desc: "sharp with minimal ringing — good default for photos",
                },
                {
                  value: "catmullrom",
                  title: "Bicubic",
                  desc: "smooth, balanced",
                },
                { value: "triangle", title: "Bilinear", desc: "" },
                {
                  value: "box",
                  title: "Area / box",
                  desc: "averages blocks, no moiré",
                },
                {
                  value: "gaussian",
                  title: "Gaussian",
                  desc: "softest, blurriest downscale",
                },
              ],
              ditherOptions: [
                { value: "none", title: "None", desc: "flat color blocks" },
                {
                  value: "ordered",
                  title: "Ordered (Bayer 4x4)",
                  desc: "fixed retro pattern",
                },
                {
                  value: "floyd",
                  title: "Floyd-Steinberg",
                  desc: "error-diffusion, smoother gradients",
                },
              ],
              sizePresets: [
                { label: "8x8", w: 8, h: 8 },
                { label: "40x32", w: 40, h: 32 },
                { label: "102x96", w: 102, h: 96 },
                { label: "320x168", w: 320, h: 168 },
                { label: "256x256", w: 256, h: 256 },
              ],
              _resultPngBytes: null,
            };
          },
          computed: {
            zoomPercent: function () {
              return Math.round(100 * this.zoomLevel);
            },
            resultZoomPercent: function () {
              return Math.round(100 * this.resultZoomLevel);
            },
            canUndoBg: function () {
              return this.undoStackSize > 0;
            },
            widthLocked: function () {
              return null != this.outputWidth;
            },
            heightLocked: function () {
              return null != this.outputHeight;
            },
            colorsLocked: function () {
              return null != this.paletteColors;
            },
            resizeAlgoLabel: function () {
              var t = this,
                e = this.resizeAlgoOptions.find(function (e) {
                  return e.value === t.resizeAlgo;
                });
              return e ? e.title : this.resizeAlgo;
            },
            ditherLabel: function () {
              var t = this,
                e = this.ditherOptions.find(function (e) {
                  return e.value === t.ditherMode;
                });
              return e ? e.title : this.ditherMode;
            },
          },
          watch: {
            outputWidth: function (t) {
              null != t && ((this.widthLocal = t), this.onSizeChange());
            },
            outputHeight: function (t) {
              null != t && ((this.heightLocal = t), this.onSizeChange());
            },
            paletteColors: function (t) {
              null != t && (this.colorsLocal = t);
            },
            imageData: function (t) {
              t && this.loadFromDataUrl(t);
            },
          },
          created: function () {
            ((this._origPanX = 0),
              (this._origPanY = 0),
              (this._resultPanX = 0),
              (this._resultPanY = 0));
          },
          mounted: function () {
            (window.addEventListener("mousemove", this.onWindowMouseMove),
              window.addEventListener("mouseup", this.onWindowMouseUp),
              window.addEventListener("touchmove", this.onWindowTouchMove, {
                passive: !1,
              }),
              window.addEventListener("touchend", this.onWindowTouchEnd),
              window.addEventListener("paste", this.handlePaste),
              window.addEventListener("resize", this.onWindowResize),
              window.addEventListener("keydown", this.onWindowKeyDown),
              this.imageData && this.loadFromDataUrl(this.imageData));
          },
          beforeDestroy: function () {
            (window.removeEventListener("mousemove", this.onWindowMouseMove),
              window.removeEventListener("mouseup", this.onWindowMouseUp),
              window.removeEventListener("touchmove", this.onWindowTouchMove),
              window.removeEventListener("touchend", this.onWindowTouchEnd),
              window.removeEventListener("paste", this.handlePaste),
              window.removeEventListener("resize", this.onWindowResize),
              window.removeEventListener("keydown", this.onWindowKeyDown),
              this._resultObjectUrl &&
                URL.revokeObjectURL(this._resultObjectUrl));
          },
          methods: j({}, Object(d["b"])(["pushNotification"]), {
            notify: function (t, e) {
              this.pushNotification({
                type: t,
                title: "Alert",
                message: e,
                duration: 3e3,
              });
            },
            getAccentColor: function () {
              var t = getComputedStyle(document.documentElement)
                .getPropertyValue("--contrast-color")
                .trim();
              return t || "#d4af37";
            },
            onFileInputChange: function (t) {
              var e = t.target.files && t.target.files[0];
              (e && this.loadFile(e), (t.target.value = ""));
            },
            onDrop: function (t) {
              this.isDraggingFile = !1;
              var e = t.dataTransfer.files && t.dataTransfer.files[0];
              e && this.loadFile(e);
            },
            loadFile: function (t) {
              var e = this;
              if (t && 0 === t.type.indexOf("image/")) {
                var a = new FileReader();
                ((a.onload = function (t) {
                  return e.loadFromDataUrl(t.target.result);
                }),
                  a.readAsDataURL(t));
              } else
                this.notify(
                  "danger",
                  "Unsupported file type: " + (t && t.type),
                );
            },
            loadFromDataUrl: function (t) {
              var e = this,
                a = new Image();
              ((a.onload = function () {
                return e.onImageLoaded(a);
              }),
                (a.onerror = function () {
                  return e.notify("danger", "Could not load image");
                }),
                (a.src = t));
            },
            handlePaste: function (t) {
              var e = this,
                a = t.clipboardData || window.clipboardData,
                n = a && a.items;
              if (n)
                for (var s = 0; s < n.length; s++) {
                  var r = n[s];
                  if (r.type && -1 !== r.type.indexOf("image")) {
                    var i = r.getAsFile();
                    if (!i) continue;
                    var o = new FileReader();
                    ((o.onload = function (t) {
                      return e.loadFromDataUrl(t.target.result);
                    }),
                      o.readAsDataURL(i),
                      t.preventDefault(),
                      this.notify("info", "Image pasted from clipboard"));
                    break;
                  }
                }
            },
            onImageLoaded: function (t) {
              var e = this;
              ((this._img = t),
                (this.srcW = t.naturalWidth),
                (this.srcH = t.naturalHeight),
                (this.loadId = Date.now()));
              var a = document.createElement("canvas");
              ((a.width = this.srcW), (a.height = this.srcH));
              var n = a.getContext("2d", { willReadFrequently: !0 });
              (n.drawImage(t, 0, 0),
                (this._srcCanvas = a),
                (this._srcCtx = n),
                (this.hasImage = !0),
                (this.hasResult = !1),
                (this.zoomIndex = 0),
                (this.zoomLevel = 1),
                (this.interactionMode = "select"),
                (this.crop =
                  "fixed" === this.cropMode
                    ? this.largestRectForAspect(
                        this.widthLocal / this.heightLocal,
                        this.srcW / 2,
                        this.srcH / 2,
                      )
                    : { x: 0, y: 0, w: this.srcW, h: this.srcH }),
                this.$nextTick(function () {
                  return e.renderOriginalCanvas();
                }));
            },
            clampCrop: function (t) {
              ((t.w = Math.max(1, Math.min(t.w, this.srcW))),
                (t.h = Math.max(1, Math.min(t.h, this.srcH))),
                (t.x = Math.max(0, Math.min(t.x, this.srcW - t.w))),
                (t.y = Math.max(0, Math.min(t.y, this.srcH - t.h))),
                (t.x = Math.round(t.x)),
                (t.y = Math.round(t.y)),
                (t.w = Math.round(t.w)),
                (t.h = Math.round(t.h)));
            },
            largestRectForAspect: function (t, e, a) {
              var n, s;
              this.srcW / this.srcH > t
                ? ((s = this.srcH), (n = s * t))
                : ((n = this.srcW), (s = n / t));
              var r = e - n / 2,
                i = a - s / 2;
              return (
                (r = Math.max(0, Math.min(r, this.srcW - n))),
                (i = Math.max(0, Math.min(i, this.srcH - s))),
                { x: r, y: i, w: n, h: s }
              );
            },
            adjustFixedCropToOutputAspect: function () {
              var t = this.widthLocal / this.heightLocal,
                e = this.crop.x + this.crop.w / 2,
                a = this.crop.y + this.crop.h / 2;
              this.crop = this.largestRectForAspect(t, e, a);
            },
            setCropMode: function (t) {
              ((this.cropMode = t),
                this.hasImage &&
                  "fixed" === t &&
                  this.adjustFixedCropToOutputAspect(),
                this.renderOriginalCanvas());
            },
            onCropFieldChange: function (t) {
              if (this.hasImage) {
                if ("fixed" === this.cropMode) {
                  var e = this.widthLocal / this.heightLocal,
                    a = this.crop.w,
                    n = this.crop.h;
                  ("h" === t ? (a = n * e) : "w" === t && (n = a / e),
                    a > this.srcW && ((a = this.srcW), (n = a / e)),
                    n > this.srcH && ((n = this.srcH), (a = n * e)),
                    (this.crop = {
                      x: this.crop.x,
                      y: this.crop.y,
                      w: a,
                      h: n,
                    }));
                }
                (this.clampCrop(this.crop), this.renderOriginalCanvas());
              }
            },
            selectAll: function () {
              this.hasImage &&
                ((this.crop =
                  "fixed" === this.cropMode
                    ? this.largestRectForAspect(
                        this.widthLocal / this.heightLocal,
                        this.srcW / 2,
                        this.srcH / 2,
                      )
                    : { x: 0, y: 0, w: this.srcW, h: this.srcH }),
                this.renderOriginalCanvas());
            },
            matchAspect: function () {
              this.hasImage &&
                ((this.crop = this.largestRectForAspect(
                  this.widthLocal / this.heightLocal,
                  this.srcW / 2,
                  this.srcH / 2,
                )),
                this.renderOriginalCanvas());
            },
            onSizeChange: function () {
              ((this.widthLocal = Math.max(
                1,
                Math.min(1024, Math.round(this.widthLocal) || 1),
              )),
                (this.heightLocal = Math.max(
                  1,
                  Math.min(1024, Math.round(this.heightLocal) || 1),
                )),
                this.hasImage &&
                  "fixed" === this.cropMode &&
                  this.adjustFixedCropToOutputAspect(),
                this.hasImage && this.renderOriginalCanvas());
            },
            applyPreset: function (t, e) {
              this.widthLocked ||
                this.heightLocked ||
                ((this.widthLocal = t),
                (this.heightLocal = e),
                this.onSizeChange());
            },
            stepColors: function (t) {
              this.colorsLocked ||
                (this.colorsLocal = Math.max(
                  2,
                  Math.min(256, (this.colorsLocal || 2) + t),
                ));
            },
            clampColors: function () {
              this.colorsLocal = Math.max(
                2,
                Math.min(256, Math.round(this.colorsLocal) || 2),
              );
            },
            selectResizeAlgo: function (t) {
              ((this.resizeAlgo = t),
                this.$refs.algoDropdown && (this.$refs.algoDropdown.open = !1));
            },
            selectDither: function (t) {
              ((this.ditherMode = t),
                this.$refs.ditherDropdown &&
                  (this.$refs.ditherDropdown.open = !1));
            },
            renderOriginalCanvas: function () {
              if (this._img) {
                var t = this.$refs.origCanvas,
                  e = this.$refs.origWrap;
                if (t && e) {
                  var a = t.getContext("2d"),
                    n = Math.min(560, e.clientWidth || 320),
                    s = Math.min(1, n / this.srcW, 380 / this.srcH),
                    r = s * this.zoomLevel,
                    i = 4e3;
                  ((r = Math.min(r, i / this.srcW, i / this.srcH)),
                    (this.displayScale = r));
                  var o = Math.max(1, Math.round(this.srcW * r)),
                    c = Math.max(1, Math.round(this.srcH * r));
                  ((t.width = o),
                    (t.height = c),
                    (a.imageSmoothingEnabled = !0),
                    a.drawImage(this._img, 0, 0, o, c));
                  var l = this.crop,
                    u = l.x * r,
                    d = l.y * r,
                    h = l.w * r,
                    p = l.h * r;
                  ((a.fillStyle = "rgba(10,12,16,0.55)"),
                    a.fillRect(0, 0, o, d),
                    a.fillRect(0, d + p, o, c - (d + p)),
                    a.fillRect(0, d, u, p),
                    a.fillRect(u + h, d, o - (u + h), p));
                  var f = this.getAccentColor();
                  ((a.strokeStyle = f),
                    (a.lineWidth = 1.5),
                    a.strokeRect(
                      u + 0.5,
                      d + 0.5,
                      Math.max(0, h - 1),
                      Math.max(0, p - 1),
                    ),
                    "fixed" === this.cropMode &&
                      ((a.fillStyle = f),
                      a.fillRect(u + h - 5, d + p - 5, 10, 10)),
                    (this._origPanX = this.clampPan(
                      this._origPanX,
                      e.clientWidth,
                      o,
                    )),
                    (this._origPanY = this.clampPan(
                      this._origPanY,
                      e.clientHeight,
                      c,
                    )),
                    (t.style.transform = "translate("
                      .concat(this._origPanX, "px, ")
                      .concat(this._origPanY, "px)")));
                }
              }
            },
            renderResultCanvas: function () {
              if (this._resultTmpCanvas) {
                var t = this.$refs.resultCanvas,
                  e = this.$refs.resultWrap;
                if (t && e) {
                  var a = this._resultW,
                    n = this._resultH,
                    s = Math.max(
                      1,
                      Math.min(8, Math.floor(380 / Math.max(a, n))),
                    ),
                    r = s * this.resultZoomLevel,
                    i = 4e3;
                  ((r = Math.min(r, i / a, i / n)),
                    (this._resultDispScale = r),
                    (t.width = Math.max(1, Math.round(a * r))),
                    (t.height = Math.max(1, Math.round(n * r))));
                  var o = t.getContext("2d");
                  ((o.imageSmoothingEnabled = !1),
                    o.clearRect(0, 0, t.width, t.height),
                    o.drawImage(this._resultTmpCanvas, 0, 0, t.width, t.height),
                    (this._resultPanX = this.clampPan(
                      this._resultPanX,
                      e.clientWidth,
                      t.width,
                    )),
                    (this._resultPanY = this.clampPan(
                      this._resultPanY,
                      e.clientHeight,
                      t.height,
                    )),
                    (t.style.transform = "translate("
                      .concat(this._resultPanX, "px, ")
                      .concat(this._resultPanY, "px)")));
                }
              }
            },
            onWindowResize: function () {
              (this.hasImage && this.renderOriginalCanvas(),
                this.hasResult && this.renderResultCanvas());
            },
            clampPan: function (t, e, a) {
              return a <= e ? (e - a) / 2 : Math.min(0, Math.max(e - a, t));
            },
            zoomIn: function () {
              var t = this.$refs.origWrap,
                e = this.$refs.origCanvas;
              if (!t || !e)
                return (
                  (this.zoomIndex = Math.min(
                    this.zoomSteps.length - 1,
                    this.zoomIndex + 1,
                  )),
                  (this.zoomLevel = this.zoomSteps[this.zoomIndex]),
                  void this.renderOriginalCanvas()
                );
              var a = this.displayScale || 1,
                n = (t.clientWidth / 2 - this._origPanX) / a,
                s = (t.clientHeight / 2 - this._origPanY) / a;
              ((this.zoomIndex = Math.min(
                this.zoomSteps.length - 1,
                this.zoomIndex + 1,
              )),
                (this.zoomLevel = this.zoomSteps[this.zoomIndex]),
                this.renderOriginalCanvas(),
                (this._origPanX = this.clampPan(
                  t.clientWidth / 2 - n * this.displayScale,
                  t.clientWidth,
                  e.width,
                )),
                (this._origPanY = this.clampPan(
                  t.clientHeight / 2 - s * this.displayScale,
                  t.clientHeight,
                  e.height,
                )),
                (e.style.transform = "translate("
                  .concat(this._origPanX, "px, ")
                  .concat(this._origPanY, "px)")));
            },
            zoomOut: function () {
              var t = this.$refs.origWrap,
                e = this.$refs.origCanvas;
              if (!t || !e)
                return (
                  (this.zoomIndex = Math.max(0, this.zoomIndex - 1)),
                  (this.zoomLevel = this.zoomSteps[this.zoomIndex]),
                  this.zoomLevel <= 1 && (this.interactionMode = "select"),
                  void this.renderOriginalCanvas()
                );
              var a = this.displayScale || 1,
                n = (t.clientWidth / 2 - this._origPanX) / a,
                s = (t.clientHeight / 2 - this._origPanY) / a;
              ((this.zoomIndex = Math.max(0, this.zoomIndex - 1)),
                (this.zoomLevel = this.zoomSteps[this.zoomIndex]),
                this.zoomLevel <= 1 && (this.interactionMode = "select"),
                this.renderOriginalCanvas(),
                (this._origPanX = this.clampPan(
                  t.clientWidth / 2 - n * this.displayScale,
                  t.clientWidth,
                  e.width,
                )),
                (this._origPanY = this.clampPan(
                  t.clientHeight / 2 - s * this.displayScale,
                  t.clientHeight,
                  e.height,
                )),
                (e.style.transform = "translate("
                  .concat(this._origPanX, "px, ")
                  .concat(this._origPanY, "px)")));
            },
            resetZoom: function () {
              ((this.zoomIndex = 0),
                (this.zoomLevel = 1),
                (this.interactionMode = "select"),
                (this._origPanX = 0),
                (this._origPanY = 0),
                this.renderOriginalCanvas());
            },
            togglePan: function () {
              this.interactionMode =
                "pan" === this.interactionMode ? "select" : "pan";
            },
            resultZoomIn: function () {
              var t = this.$refs.resultWrap,
                e = this.$refs.resultCanvas;
              if (!t || !e)
                return (
                  (this.resultZoomIndex = Math.min(
                    this.resultZoomSteps.length - 1,
                    this.resultZoomIndex + 1,
                  )),
                  (this.resultZoomLevel =
                    this.resultZoomSteps[this.resultZoomIndex]),
                  void this.renderResultCanvas()
                );
              var a = this._resultDispScale || 1,
                n = (t.clientWidth / 2 - this._resultPanX) / a,
                s = (t.clientHeight / 2 - this._resultPanY) / a;
              ((this.resultZoomIndex = Math.min(
                this.resultZoomSteps.length - 1,
                this.resultZoomIndex + 1,
              )),
                (this.resultZoomLevel =
                  this.resultZoomSteps[this.resultZoomIndex]),
                this.renderResultCanvas(),
                (this._resultPanX = this.clampPan(
                  t.clientWidth / 2 - n * this._resultDispScale,
                  t.clientWidth,
                  e.width,
                )),
                (this._resultPanY = this.clampPan(
                  t.clientHeight / 2 - s * this._resultDispScale,
                  t.clientHeight,
                  e.height,
                )),
                (e.style.transform = "translate("
                  .concat(this._resultPanX, "px, ")
                  .concat(this._resultPanY, "px)")));
            },
            resultZoomOut: function () {
              var t = this.$refs.resultWrap,
                e = this.$refs.resultCanvas;
              if (!t || !e)
                return (
                  (this.resultZoomIndex = Math.max(
                    0,
                    this.resultZoomIndex - 1,
                  )),
                  (this.resultZoomLevel =
                    this.resultZoomSteps[this.resultZoomIndex]),
                  this.resultZoomLevel <= 1 &&
                    (this.resultInteractionMode = "select"),
                  void this.renderResultCanvas()
                );
              var a = this._resultDispScale || 1,
                n = (t.clientWidth / 2 - this._resultPanX) / a,
                s = (t.clientHeight / 2 - this._resultPanY) / a;
              ((this.resultZoomIndex = Math.max(0, this.resultZoomIndex - 1)),
                (this.resultZoomLevel =
                  this.resultZoomSteps[this.resultZoomIndex]),
                this.resultZoomLevel <= 1 &&
                  (this.resultInteractionMode = "select"),
                this.renderResultCanvas(),
                (this._resultPanX = this.clampPan(
                  t.clientWidth / 2 - n * this._resultDispScale,
                  t.clientWidth,
                  e.width,
                )),
                (this._resultPanY = this.clampPan(
                  t.clientHeight / 2 - s * this._resultDispScale,
                  t.clientHeight,
                  e.height,
                )),
                (e.style.transform = "translate("
                  .concat(this._resultPanX, "px, ")
                  .concat(this._resultPanY, "px)")));
            },
            resultResetZoom: function () {
              ((this.resultZoomIndex = 0),
                (this.resultZoomLevel = 1),
                (this.resultInteractionMode = "select"),
                (this._resultPanX = 0),
                (this._resultPanY = 0),
                this.renderResultCanvas());
            },
            toggleResultPan: function () {
              this.resultInteractionMode =
                "pan" === this.resultInteractionMode ? "select" : "pan";
            },
            onResultMouseDown: function (t) {
              if (this.hasResult)
                return "pan" === this.resultInteractionMode
                  ? ((this._resultPanStart = {
                      x: t.clientX,
                      y: t.clientY,
                      panX: this._resultPanX,
                      panY: this._resultPanY,
                    }),
                    void (this._resultPanning = !0))
                  : void (
                      "eraser" === this.bgRemovalMode &&
                      this.beginEraserStroke(
                        this.resultCanvasPosFromClient(t.clientX, t.clientY),
                      )
                    );
            },
            onResultTouchStart: function (t) {
              if (this.hasResult) {
                if ("pan" === this.resultInteractionMode) {
                  t.preventDefault();
                  var e = t.touches[0];
                  return (
                    (this._resultPanStart = {
                      x: e.clientX,
                      y: e.clientY,
                      panX: this._resultPanX,
                      panY: this._resultPanY,
                    }),
                    void (this._resultPanning = !0)
                  );
                }
                if ("eraser" === this.bgRemovalMode) {
                  t.preventDefault();
                  var a = t.touches[0];
                  this.beginEraserStroke(
                    this.resultCanvasPosFromClient(a.clientX, a.clientY),
                  );
                }
              }
            },
            onResultHoverMove: function () {
              if (
                this.hasResult &&
                !this._resultPanning &&
                !this._eraserStroke
              ) {
                var t = this.$refs.resultCanvas;
                t &&
                  (t.style.cursor =
                    "pan" === this.resultInteractionMode
                      ? "grab"
                      : "crosshair");
              }
            },
            canvasPosFromClient: function (t, e) {
              var a = this.$refs.origCanvas,
                n = a.getBoundingClientRect(),
                s = (t - n.left) * (a.width / n.width),
                r = (e - n.top) * (a.height / n.height);
              return { x: s / this.displayScale, y: r / this.displayScale };
            },
            canvasPosFromEvent: function (t) {
              return this.canvasPosFromClient(t.clientX, t.clientY);
            },
            touchPos: function (t) {
              var e = t.touches[0] || t.changedTouches[0];
              return this.canvasPosFromClient(e.clientX, e.clientY);
            },
            resultCanvasPosFromClient: function (t, e) {
              var a = this.$refs.resultCanvas,
                n = a.getBoundingClientRect(),
                s = (t - n.left) * (a.width / n.width),
                r = (e - n.top) * (a.height / n.height),
                i = this._resultDispScale || 1;
              return { x: s / i, y: r / i };
            },
            pointInRect: function (t, e) {
              return (
                t.x >= e.x && t.x <= e.x + e.w && t.y >= e.y && t.y <= e.y + e.h
              );
            },
            hitTestHandle: function (t) {
              var e = this.crop,
                a = 10 / this.displayScale;
              return (
                Math.abs(t.x - (e.x + e.w)) <= a &&
                Math.abs(t.y - (e.y + e.h)) <= a
              );
            },
            beginDrag: function (t) {
              if ("fixed" === this.cropMode)
                if (this.hitTestHandle(t))
                  this.dragState = {
                    mode: "resize",
                    startX: t.x,
                    startY: t.y,
                    orig: j({}, this.crop),
                  };
                else if (this.pointInRect(t, this.crop))
                  this.dragState = {
                    mode: "move",
                    startX: t.x,
                    startY: t.y,
                    orig: j({}, this.crop),
                  };
                else {
                  var e = Math.max(
                      0,
                      Math.min(t.x - this.crop.w / 2, this.srcW - this.crop.w),
                    ),
                    a = Math.max(
                      0,
                      Math.min(t.y - this.crop.h / 2, this.srcH - this.crop.h),
                    );
                  ((this.crop = { x: e, y: a, w: this.crop.w, h: this.crop.h }),
                    this.renderOriginalCanvas(),
                    (this.dragState = {
                      mode: "move",
                      startX: t.x,
                      startY: t.y,
                      orig: j({}, this.crop),
                    }));
                }
              else this.dragState = { startX: t.x, startY: t.y };
            },
            continueDrag: function (t) {
              if (this.dragState && this.hasImage) {
                if ("move" === this.dragState.mode) {
                  var e = t.x - this.dragState.startX,
                    a = t.y - this.dragState.startY,
                    n = this.dragState.orig,
                    s = Math.max(0, Math.min(n.x + e, this.srcW - n.w)),
                    r = Math.max(0, Math.min(n.y + a, this.srcH - n.h));
                  this.crop = { x: s, y: r, w: n.w, h: n.h };
                } else if ("resize" === this.dragState.mode) {
                  var i = this.widthLocal / this.heightLocal,
                    o = this.dragState.orig,
                    c = t.x - this.dragState.startX,
                    l = Math.max(8, Math.min(o.w + c, this.srcW - o.x)),
                    u = l / i;
                  (o.y + u > this.srcH && ((u = this.srcH - o.y), (l = u * i)),
                    (this.crop = { x: o.x, y: o.y, w: l, h: u }));
                } else {
                  var d = Math.min(this.dragState.startX, t.x),
                    h = Math.max(this.dragState.startX, t.x),
                    p = Math.min(this.dragState.startY, t.y),
                    f = Math.max(this.dragState.startY, t.y);
                  ((this.crop = {
                    x: d,
                    y: p,
                    w: Math.max(1, h - d),
                    h: Math.max(1, f - p),
                  }),
                    this.clampCrop(this.crop));
                }
                this.renderOriginalCanvas();
              }
            },
            onCanvasMouseDown: function (t) {
              if (this.hasImage)
                return "pan" === this.interactionMode
                  ? ((this._panStart = {
                      x: t.clientX,
                      y: t.clientY,
                      panX: this._origPanX,
                      panY: this._origPanY,
                    }),
                    void (this.dragState = { mode: "pan" }))
                  : void this.beginDrag(this.canvasPosFromEvent(t));
            },
            onCanvasHoverMove: function (t) {
              if (this.hasImage && !this.dragState) {
                var e = this.$refs.origCanvas;
                if ("pan" !== this.interactionMode)
                  if ("fixed" === this.cropMode) {
                    var a = this.canvasPosFromEvent(t);
                    this.hitTestHandle(a)
                      ? (e.style.cursor = "nwse-resize")
                      : this.pointInRect(a, this.crop)
                        ? (e.style.cursor = "move")
                        : (e.style.cursor = "crosshair");
                  } else e.style.cursor = "crosshair";
                else e.style.cursor = "grab";
              }
            },
            onWindowMouseMove: function (t) {
              if (this._resultPanning) {
                var e = this.$refs.resultWrap,
                  a = this.$refs.resultCanvas,
                  n = t.clientX - this._resultPanStart.x,
                  s = t.clientY - this._resultPanStart.y;
                return (
                  (this._resultPanX = this.clampPan(
                    this._resultPanStart.panX + n,
                    e.clientWidth,
                    a.width,
                  )),
                  (this._resultPanY = this.clampPan(
                    this._resultPanStart.panY + s,
                    e.clientHeight,
                    a.height,
                  )),
                  void (a.style.transform = "translate("
                    .concat(this._resultPanX, "px, ")
                    .concat(this._resultPanY, "px)"))
                );
              }
              if (this._eraserStroke)
                this.continueEraserStroke(
                  this.resultCanvasPosFromClient(t.clientX, t.clientY),
                );
              else {
                if (this.dragState && "pan" === this.dragState.mode) {
                  var r = this.$refs.origWrap,
                    i = this.$refs.origCanvas,
                    o = t.clientX - this._panStart.x,
                    c = t.clientY - this._panStart.y;
                  return (
                    (this._origPanX = this.clampPan(
                      this._panStart.panX + o,
                      r.clientWidth,
                      i.width,
                    )),
                    (this._origPanY = this.clampPan(
                      this._panStart.panY + c,
                      r.clientHeight,
                      i.height,
                    )),
                    void (i.style.transform = "translate("
                      .concat(this._origPanX, "px, ")
                      .concat(this._origPanY, "px)"))
                  );
                }
                this.continueDrag(this.canvasPosFromEvent(t));
              }
            },
            onWindowMouseUp: function () {
              ((this.dragState = null),
                (this._resultPanning = !1),
                this._eraserStroke && this.endEraserStroke());
            },
            onCanvasTouchStart: function (t) {
              if (this.hasImage) {
                if ("pan" === this.interactionMode) {
                  t.preventDefault();
                  var e = t.touches[0];
                  return (
                    (this._panStart = {
                      x: e.clientX,
                      y: e.clientY,
                      panX: this._origPanX,
                      panY: this._origPanY,
                    }),
                    void (this.dragState = { mode: "pan" })
                  );
                }
                (t.preventDefault(), this.beginDrag(this.touchPos(t)));
              }
            },
            onWindowTouchMove: function (t) {
              if (this._resultPanning) {
                t.preventDefault();
                var e = t.touches[0],
                  a = this.$refs.resultWrap,
                  n = this.$refs.resultCanvas,
                  s = e.clientX - this._resultPanStart.x,
                  r = e.clientY - this._resultPanStart.y;
                return (
                  (this._resultPanX = this.clampPan(
                    this._resultPanStart.panX + s,
                    a.clientWidth,
                    n.width,
                  )),
                  (this._resultPanY = this.clampPan(
                    this._resultPanStart.panY + r,
                    a.clientHeight,
                    n.height,
                  )),
                  void (n.style.transform = "translate("
                    .concat(this._resultPanX, "px, ")
                    .concat(this._resultPanY, "px)"))
                );
              }
              if (this._eraserStroke) {
                t.preventDefault();
                var i = t.touches[0];
                this.continueEraserStroke(
                  this.resultCanvasPosFromClient(i.clientX, i.clientY),
                );
              } else {
                if (this.dragState && "pan" === this.dragState.mode) {
                  t.preventDefault();
                  var o = t.touches[0],
                    c = this.$refs.origWrap,
                    l = this.$refs.origCanvas,
                    u = o.clientX - this._panStart.x,
                    d = o.clientY - this._panStart.y;
                  return (
                    (this._origPanX = this.clampPan(
                      this._panStart.panX + u,
                      c.clientWidth,
                      l.width,
                    )),
                    (this._origPanY = this.clampPan(
                      this._panStart.panY + d,
                      c.clientHeight,
                      l.height,
                    )),
                    void (l.style.transform = "translate("
                      .concat(this._origPanX, "px, ")
                      .concat(this._origPanY, "px)"))
                  );
                }
                this.dragState &&
                  (t.preventDefault(), this.continueDrag(this.touchPos(t)));
              }
            },
            onWindowTouchEnd: function () {
              ((this.dragState = null),
                (this._resultPanning = !1),
                this._eraserStroke && this.endEraserStroke());
            },
            onWindowKeyDown: function (t) {
              var e = (t.key || "").toLowerCase();
              if ((t.ctrlKey || t.metaKey) && !t.shiftKey && "z" === e) {
                var a = document.activeElement,
                  n = a && a.tagName;
                if (
                  "INPUT" === n ||
                  "TEXTAREA" === n ||
                  (a && a.isContentEditable)
                )
                  return;
                this.canUndoBg && (t.preventDefault(), this.undoEdit());
              }
            },
            beginEraserStroke: function (t) {
              this.hasResult &&
                (this.pushUndoSnapshot(),
                (this._eraserStroke = { lastX: t.x, lastY: t.y }),
                this.stampEraser(t.x, t.y));
            },
            continueEraserStroke: function (t) {
              if (this._eraserStroke) {
                for (
                  var e = this._eraserStroke,
                    a = e.lastX,
                    n = e.lastY,
                    s = Math.hypot(t.x - a, t.y - n),
                    r = Math.max(0.5, this.eraserSize / 3),
                    i = Math.max(1, Math.ceil(s / r)),
                    o = 1;
                  o <= i;
                  o++
                ) {
                  var c = o / i;
                  this.stampEraser(a + (t.x - a) * c, n + (t.y - n) * c);
                }
                ((this._eraserStroke.lastX = t.x),
                  (this._eraserStroke.lastY = t.y));
              }
            },
            endEraserStroke: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t() {
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            if (this._eraserStroke) {
                              t.next = 2;
                              break;
                            }
                            return t.abrupt("return");
                          case 2:
                            return (
                              (this._eraserStroke = null),
                              (t.next = 5),
                              this.commitResultEdit()
                            );
                          case 5:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                  );
                }),
              );
              function e() {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            stampEraser: function (t, e) {
              if (this._resultIndices && this._resultW) {
                var a = wt(
                  this._resultIndices,
                  this.resultPalette,
                  this._resultW,
                  this._resultH,
                  this.resultTransparentIndex,
                  t,
                  e,
                  this.eraserSize,
                  this.eraserHardness,
                );
                ((this._resultIndices = a.indices),
                  (this.resultPalette = a.palette),
                  null !== a.transparentIndex
                    ? (a.reindexed &&
                        this.notify(
                          "info",
                          "Palette was full — merged the two most similar colors to free a transparency slot. Future edits on this image won't need to do that again.",
                        ),
                      (this.resultTransparentIndex = a.transparentIndex),
                      a.changed > 0 && this.rebuildResultPreviewBitmap())
                    : this.notify(
                        "danger",
                        "Could not erase: no room left for transparency.",
                      ));
              }
            },
            swatchStyle: function (t) {
              if (t === this.resultTransparentIndex) return {};
              var e = this.resultPalette[t];
              return {
                background: "rgb(" + e[0] + "," + e[1] + "," + e[2] + ")",
              };
            },
            blobToDataUrl: function (t) {
              return new Promise(function (e, a) {
                var n = new FileReader();
                ((n.onload = function () {
                  return e(n.result);
                }),
                  (n.onerror = a),
                  n.readAsDataURL(t));
              });
            },
            rebuildResultPreviewBitmap: function () {
              var t = this._resultW,
                e = this._resultH;
              if (t && e && this._resultIndices && this.resultPalette) {
                for (
                  var a = new Uint8ClampedArray(t * e * 4),
                    n = this.resultPalette,
                    s = this._resultIndices,
                    r = this.resultTransparentIndex,
                    i = null !== r && void 0 !== r,
                    o = 0;
                  o < t * e;
                  o++
                ) {
                  var c = s[o],
                    l = n[c];
                  ((a[4 * o] = l[0]),
                    (a[4 * o + 1] = l[1]),
                    (a[4 * o + 2] = l[2]),
                    (a[4 * o + 3] = i && c === r ? 0 : 255));
                }
                var u = this._resultTmpCanvas;
                ((u && u.width === t && u.height === e) ||
                  ((u = document.createElement("canvas")),
                  (u.width = t),
                  (u.height = e),
                  (this._resultTmpCanvas = u)),
                  u.getContext("2d").putImageData(new ImageData(a, t, e), 0, 0),
                  this.renderResultCanvas());
              }
            },
            commitResultEdit: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t() {
                  var e, a, n, s, r, i, o, c, l;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            return (
                              (e = this._resultW),
                              (a = this._resultH),
                              (n = this.resultPalette),
                              (s = this._resultIndices),
                              (r = this.resultTransparentIndex),
                              (i = null !== r && void 0 !== r),
                              (t.next = 5),
                              B(e, a, s, n, r)
                            );
                          case 5:
                            return (
                              (o = t.sent),
                              (this._resultPngBytes = o),
                              (c = $(n.length)),
                              (this.resultStatus =
                                e +
                                "x" +
                                a +
                                "px · " +
                                n.length +
                                " colors (" +
                                c +
                                "bpp) · " +
                                (o.length / 1024).toFixed(1) +
                                " KB" +
                                (i ? " · has transparency" : "")),
                              this._resultObjectUrl &&
                                URL.revokeObjectURL(this._resultObjectUrl),
                              (l = new Blob([o], { type: "image/png" })),
                              (this._resultObjectUrl = URL.createObjectURL(l)),
                              (t.next = 14),
                              this.blobToDataUrl(l)
                            );
                          case 14:
                            ((this.resultDataUrl = t.sent),
                              (this._resultGeneration =
                                (this._resultGeneration || 0) + 1));
                          case 16:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                  );
                }),
              );
              function e() {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            saveCurrentToCatalog: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t() {
                  var e;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            if (
                              this._resultPngBytes &&
                              this._resultW &&
                              this._resultH
                            ) {
                              t.next = 3;
                              break;
                            }
                            return (
                              this.notify(
                                "danger",
                                "Nothing to save yet — generate an image first.",
                              ),
                              t.abrupt("return")
                            );
                          case 3:
                            if (this.loadId) {
                              t.next = 5;
                              break;
                            }
                            return t.abrupt("return");
                          case 5:
                            return (
                              (e = new Blob([this._resultPngBytes], {
                                type: "image/png",
                              })),
                              (t.prev = 6),
                              (t.next = 9),
                              b({
                                id: this.loadId,
                                blob: e,
                                width: this._resultW,
                                height: this._resultH,
                                colors: Math.max(
                                  2,
                                  Math.min(
                                    256,
                                    Math.round(this.colorsLocal) || 16,
                                  ),
                                ),
                                updatedAt: Date.now(),
                              })
                            );
                          case 9:
                            (this.notify("success", "Saved to catalog"),
                              (t.next = 15));
                            break;
                          case 12:
                            ((t.prev = 12),
                              (t.t0 = t["catch"](6)),
                              this.notify(
                                "danger",
                                "Could not save to catalog: " +
                                  (t.t0 && t.t0.message),
                              ));
                          case 15:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                    [[6, 12]],
                  );
                }),
              );
              function e() {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            onCatalogSelect: function (t) {
              ((this.catalogVisible = !1), this.loadFromDataUrl(t));
            },
            finalizeResult: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t(e, a, n, s, r) {
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            return (
                              (this._resultIndices = n),
                              (this._resultW = e),
                              (this._resultH = a),
                              (this.resultPalette = s),
                              (this.resultTransparentIndex = r),
                              (this.resultDims = e + "x" + a + "px"),
                              (this.hasResult = !0),
                              (t.next = 9),
                              this.$nextTick()
                            );
                          case 9:
                            return (
                              this.rebuildResultPreviewBitmap(),
                              (t.next = 12),
                              this.commitResultEdit()
                            );
                          case 12:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                  );
                }),
              );
              function e(e, a, n, s, r) {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            generate: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t() {
                  var e, a, n, s, r, i, o, c, l, u, d, h, p, f, m, g, v;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            if (this.hasImage && !this.isProcessing) {
                              t.next = 2;
                              break;
                            }
                            return t.abrupt("return");
                          case 2:
                            return (
                              (this.isProcessing = !0),
                              (this._undoStack = []),
                              (this.undoStackSize = 0),
                              (this.resultZoomIndex = 0),
                              (this.resultZoomLevel = 1),
                              (this.resultInteractionMode = "select"),
                              (this._resultPanX = 0),
                              (this._resultPanY = 0),
                              (t.next = 12),
                              new Promise(function (t) {
                                return setTimeout(t, 20);
                              })
                            );
                          case 12:
                            return (
                              (t.prev = 12),
                              (e = this.crop),
                              (a = Math.round(e.x)),
                              (n = Math.round(e.y)),
                              (s = Math.round(e.w)),
                              (r = Math.round(e.h)),
                              (i = this._srcCtx.getImageData(a, n, s, r).data),
                              (o = Math.max(
                                1,
                                Math.min(
                                  1024,
                                  Math.round(this.widthLocal) || 1,
                                ),
                              )),
                              (c = Math.max(
                                1,
                                Math.min(
                                  1024,
                                  Math.round(this.heightLocal) || 1,
                                ),
                              )),
                              (l = this.resizeAlgo),
                              "auto" === l &&
                                ((u = (o * c) / (s * r)),
                                (l = u < 1 ? "lanczos3" : "nearest")),
                              (d =
                                "nearest" === l
                                  ? nt(i, s, r, o, c)
                                  : at(i, s, r, o, c, l)),
                              (h =
                                this.edgeSmoothing > 0
                                  ? rt(d, o, c, it[this.edgeSmoothing])
                                  : d),
                              (p = Math.max(
                                2,
                                Math.min(
                                  256,
                                  Math.round(this.colorsLocal) || 16,
                                ),
                              )),
                              (f = ht(h, o, c, p, this.ditherMode)),
                              (m = f.indices),
                              (g = f.palette),
                              (v = f.transparentIndex),
                              (t.next = 26),
                              this.finalizeResult(o, c, m, g, v)
                            );
                          case 26:
                            (this.notify(
                              "success",
                              "Image generated: " + this.resultStatus,
                            ),
                              (t.next = 32));
                            break;
                          case 29:
                            ((t.prev = 29),
                              (t.t0 = t["catch"](12)),
                              this.notify(
                                "danger",
                                "Failed to generate image: " +
                                  (t.t0 && t.t0.message),
                              ));
                          case 32:
                            return (
                              (t.prev = 32),
                              (this.isProcessing = !1),
                              t.finish(32)
                            );
                          case 35:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                    [[12, 29, 32, 35]],
                  );
                }),
              );
              function e() {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            onResultCanvasClick: function (t) {
              if (
                this.hasResult &&
                this._resultIndices &&
                "pan" !== this.resultInteractionMode &&
                "eraser" !== this.bgRemovalMode
              ) {
                var e = this.resultCanvasPosFromClient(t.clientX, t.clientY),
                  a = Math.min(this._resultW - 1, Math.max(0, Math.floor(e.x))),
                  n = Math.min(this._resultH - 1, Math.max(0, Math.floor(e.y)));
                this.applyBackgroundRemoval(a, n);
              }
            },
            pushUndoSnapshot: function () {
              (this._undoStack || (this._undoStack = []),
                this._undoStack.push({
                  indices: this._resultIndices
                    ? this._resultIndices.slice()
                    : this._resultIndices,
                  palette: this.resultPalette
                    ? this.resultPalette.slice()
                    : this.resultPalette,
                  transparentIndex: this.resultTransparentIndex,
                  w: this._resultW,
                  h: this._resultH,
                }),
                this._undoStack.length > 10 && this._undoStack.shift(),
                (this.undoStackSize = this._undoStack.length));
            },
            undoEdit: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t() {
                  var e;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            if (
                              this._undoStack &&
                              0 !== this._undoStack.length
                            ) {
                              t.next = 2;
                              break;
                            }
                            return t.abrupt("return");
                          case 2:
                            return (
                              (e = this._undoStack.pop()),
                              (this.undoStackSize = this._undoStack.length),
                              (t.next = 6),
                              this.finalizeResult(
                                e.w,
                                e.h,
                                e.indices,
                                e.palette,
                                e.transparentIndex,
                              )
                            );
                          case 6:
                            this.notify("info", "Undone");
                          case 7:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                  );
                }),
              );
              function e() {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            applyBackgroundRemoval: (function () {
              var t = Object(c["a"])(
                regeneratorRuntime.mark(function t(e, a) {
                  var n, s, r, i, o;
                  return regeneratorRuntime.wrap(
                    function (t) {
                      while (1)
                        switch ((t.prev = t.next)) {
                          case 0:
                            if (
                              ((n = this._resultW),
                              (s = this._resultH),
                              (r = this._resultIndices),
                              (i = r[a * n + e]),
                              "color" !== this.bgRemovalMode)
                            ) {
                              t.next = 7;
                              break;
                            }
                            ((o = vt(
                              r,
                              this.resultPalette,
                              this.resultTransparentIndex,
                              i,
                              this.bgTolerance,
                            )),
                              (t.next = 12));
                            break;
                          case 7:
                            if ("smart" !== this.bgRemovalMode) {
                              t.next = 11;
                              break;
                            }
                            ((o = bt(
                              r,
                              this.resultPalette,
                              n,
                              s,
                              this.resultTransparentIndex,
                              e,
                              a,
                              this.bgTolerance,
                            )),
                              (t.next = 12));
                            break;
                          case 11:
                            return t.abrupt("return");
                          case 12:
                            if (o) {
                              t.next = 15;
                              break;
                            }
                            return (
                              this.notify(
                                "danger",
                                "Could not remove background: the palette has too few colors to free a transparency slot.",
                              ),
                              t.abrupt("return")
                            );
                          case 15:
                            if (0 !== o.changed) {
                              t.next = 18;
                              break;
                            }
                            return (
                              this.notify(
                                "info",
                                "No matching pixels found — try increasing the tolerance.",
                              ),
                              t.abrupt("return")
                            );
                          case 18:
                            return (
                              this.pushUndoSnapshot(),
                              (t.next = 21),
                              this.finalizeResult(
                                n,
                                s,
                                o.indices,
                                o.palette,
                                o.transparentIndex,
                              )
                            );
                          case 21:
                            (o.reindexed &&
                              this.notify(
                                "info",
                                "Palette was full — merged the two most similar colors to free a transparency slot. Future removals on this image won't need to do that again.",
                              ),
                              this.notify(
                                "success",
                                o.changed + " pixel(s) made transparent",
                              ));
                          case 23:
                          case "end":
                            return t.stop();
                        }
                    },
                    t,
                    this,
                  );
                }),
              );
              function e(e, a) {
                return t.apply(this, arguments);
              }
              return e;
            })(),
            downloadResult: function () {
              if (this._resultObjectUrl) {
                var t = document.createElement("a");
                ((t.href = this._resultObjectUrl),
                  (t.download = "indexed_texture.png"),
                  document.body.appendChild(t),
                  t.click(),
                  document.body.removeChild(t),
                  this.$emit("save", !0));
              }
            },
            confirmResult: function () {
              if (this._resultPngBytes) {
                var t = this._resultPngBytes,
                  e = new DataView(t.buffer, t.byteOffset, t.byteLength);
                (this.notify("info", "Please wait the data is saving in file"),
                  this.$emit("confirm", e));
              } else this.notify("danger", "No result to confirm yet");
            },
          }),
        },
        xt = yt,
        Ct = (a("debf"), Object(I["a"])(xt, n, s, !1, null, "4c6bb64e", null));
      e["a"] = Ct.exports;
    },
    5645: function (t, e, a) {
      "use strict";
      (a.d(e, "d", function () {
        return n;
      }),
        a.d(e, "b", function () {
          return s;
        }),
        a.d(e, "a", function () {
          return r;
        }),
        a.d(e, "c", function () {
          return i;
        }),
        a.d(e, "e", function () {
          return o;
        }),
        a.d(e, "g", function () {
          return c;
        }),
        a.d(e, "f", function () {
          return l;
        }),
        a.d(e, "h", function () {
          return u;
        }));
      var n = {
          l0: " ",
          l1: "e",
          l2: "t",
          l3: "a",
          l4: "o",
          l5: "i",
          l6: "n",
          l7: "s",
          l8: "r",
          l9: "h",
          l10: "l",
          l11: ".",
          l12: "d",
          l13: "u",
          l14: "m",
          l15: "c",
          l16: "g",
          l17: "y",
          l18: "w",
          l19: "f",
          l20: "p",
          l21: "b",
          l22: "k",
          l23: "!",
          l24: "A",
          l25: "v",
          l26: "I",
          l27: "'",
          l28: "T",
          l29: "S",
          l30: "M",
          l31: ",",
          l32: "D",
          l33: "O",
          l34: "W",
          l35: "H",
          l36: "Y",
          l37: "E",
          l38: "R",
          l39: "<",
          l40: ">",
          l41: "G",
          l42: "L",
          l43: "C",
          l44: "N",
          l45: "B",
          l46: "?",
          l47: "P",
          l48: "-",
          l49: "F",
          l50: "z",
          l51: "K",
          l52: "j",
          l53: "U",
          l54: "x",
          l55: "q",
          l56: "0",
          l57: "V",
          l58: "2",
          l59: "J",
          l60: "#",
          l61: "1",
          l62: "Q",
          l63: "Z",
          l64: '"',
          l65: "3",
          l66: "5",
          l67: "&",
          l68: "/",
          l69: "7",
          l70: "X",
          l71: " ",
          l72: ":",
          l73: " ",
          l74: "4",
          l75: ")",
          l76: "(",
          l77: " ",
          l78: "6",
          l79: "$",
          l80: "*",
          l81: ">",
          l82: " ",
          l83: " ",
          l84: "<",
          l85: "α",
          l86: "+",
          l87: "8",
          l88: "←",
          l89: "9",
          l90: "→",
          l91: "%",
          l92: " ",
          l93: " ",
          l94: " ",
          l95: " ",
          l96: " ",
          l97: " ",
          l98: " ",
          l99: " ",
          l100: " ",
          l101: " ",
          l102: " ",
          l103: " ",
          l104: " ",
          l105: " ",
          l106: " ",
          l107: " ",
          l108: " ",
          l109: " ",
          l110: " ",
          l111: " ",
          l112: " ",
          l113: " ",
          l114: " ",
          l115: " ",
          l116: " ",
          l117: " ",
          l118: " ",
          l119: " ",
          l120: " ",
          l121: " ",
          l122: " ",
          l123: " ",
          l124: " ",
          l125: " ",
          l126: " ",
          l127: " ",
          l128: " ",
          l129: " ",
          l130: " ",
          l131: " ",
          l132: " ",
          l133: " ",
          l134: " ",
          l135: " ",
          l136: " ",
          l137: " ",
          l138: " ",
          l139: " ",
          l140: " ",
          l141: " ",
          l142: " ",
          l143: " ",
          l144: " ",
          l145: " ",
          l146: " ",
          l147: " ",
          l148: " ",
          l149: " ",
          l150: " ",
          l151: " ",
          l152: " ",
          l153: " ",
          l154: " ",
          l155: " ",
          l156: " ",
          l157: " ",
          l158: " ",
          l159: " ",
          l160: " ",
          l161: " ",
          l162: " ",
          l163: " ",
          l164: " ",
          l165: " ",
          l166: " ",
          l167: " ",
          l168: " ",
          l169: " ",
          l170: " ",
          l171: " ",
          l172: " ",
          l173: " ",
          l174: " ",
          l175: " ",
          l176: " ",
          l177: " ",
          l178: " ",
          l179: " ",
          l180: " ",
          l181: " ",
          l182: " ",
          l183: " ",
          l184: " ",
          l185: " ",
          l186: " ",
          l187: " ",
          l188: " ",
          l189: " ",
          l190: " ",
          l191: " ",
          l192: " ",
          l193: " ",
          l194: " ",
          l195: " ",
          l196: " ",
          l197: " ",
          l198: " ",
          l199: " ",
          l200: " ",
          l201: " ",
          l202: " ",
          l203: " ",
          l204: " ",
          l205: " ",
          l206: " ",
          l207: " ",
          l208: " ",
          l209: " ",
          l210: " ",
          l211: " ",
          l212: " ",
          l213: " ",
          l214: " ",
          l215: " ",
          l216: " ",
          l217: " ",
          l218: " ",
          l219: " ",
          l220: " ",
          l221: " ",
          l222: " ",
          l223: " ",
          l224: " ",
          l225: " ",
          l226: " ",
          l227: " ",
          l228: " ",
          l229: " ",
          l230: " ",
          l231: " ",
          l232: " ",
          l233: " ",
          l234: " ",
          l235: " ",
          l236: " ",
          l237: " ",
          l238: " ",
          l239: " ",
        },
        s = { l254: "↵", l255: "☒", l250: "⎘", l251: "⇶" },
        r = [
          { name: "White", param: 0 },
          { name: "Yellow", param: 1 },
          { name: "Blue", param: 2 },
          { name: "Purple", param: 3 },
          { name: "Grey", param: 4 },
          { name: "Orange", param: 5 },
          { name: "Red", param: 6 },
          { name: "Green", param: 7 },
        ],
        i = [
          { name: "SLIDE IN LEFT", param: "00" },
          { name: "SLIDE IN RIGHT", param: "01" },
          { name: "APPEAR AT LEFT", param: "08" },
          { name: "APPEAR AT RIGHT", param: "09" },
          { name: "SLIDE IN LEFT STATE 3", param: "14" },
          { name: "SLIDE IN RIGHT STATE 3", param: "15" },
          { name: "SLIDE OUT", param: "80" },
          { name: "OUT 1", param: "81" },
          { name: "OUT 2", param: "82" },
          { name: "SHOW STATE 1", param: "40" },
          { name: "SHOW STATE 2", param: "41" },
          { name: "DE-FREEZE ANIMATION 1", param: "20" },
          { name: "FREEZE ANIMATION 1", param: "21" },
        ],
        o = [
          { name: "3D BATTLE THEME", p1: 128, p2: 114 },
          { name: "3D DUEL EGYPT THEME", p1: 160, p2: 114 },
          { name: "BUILD DECK", p1: 224, p2: 112 },
          { name: "CARD SHOP", p1: 144, p2: 112 },
          { name: "DARK NITE'S ARRIVAL", p1: 192, p2: 113 },
          { name: "DARK SHRINE", p1: 112, p2: 113 },
          { name: "DARKNITE & NITEMARE THEME", p1: 96, p2: 114 },
          { name: "DARKNITE & NITEMARE THEME", p1: 80, p2: 114 },
          { name: "DARKNITE 3D BATTLE THEME", p1: 176, p2: 114 },
          { name: "DESERT SHRINE", p1: 48, p2: 113 },
          { name: "EGYPT IN RUINS", p1: 208, p2: 112 },
          { name: "EGYPTIAN DUEL THEME", p1: 0, p2: 114 },
          { name: "FINAL'S FACE-OFF", p1: 112, p2: 112 },
          { name: "FINAL'S MATCH THEME", p1: 224, p2: 113 },
          { name: "FORBIDDEN RUINS", p1: 144, p2: 113 },
          { name: "FOREST SHRINE", p1: 32, p2: 113 },
          { name: "FREEDUEL SELECT THEME", p1: 192, p2: 114 },
          { name: "FREEDUEL THEME", p1: 112, p2: 114 },
          { name: "HEISHIN INVASION", p1: 176, p2: 113 },
          { name: "HEISHIN MILLENIUM PUZZLE", p1: 160, p2: 113 },
          { name: "HENSHIN THEME", p1: 48, p2: 114 },
          { name: "HIDDEN CARD SHOP", p1: 240, p2: 112 },
          { name: "HIGHMAGE DUEL THEME", p1: 32, p2: 114 },
          { name: "INPUT NAME MENU", p1: 16, p2: 112 },
          { name: "INSIDE THE PUZZLE", p1: 80, p2: 112 },
          { name: "INTRODUCTION TITLE SCREEN", p1: 32, p2: 112 },
          { name: "MAGE DUEL THEME", p1: 16, p2: 114 },
          { name: "MAIN MENU", p1: 0, p2: 112 },
          { name: "MEADOW SHRINE", p1: 64, p2: 113 },
          { name: "METROPOLIS I", p1: 160, p2: 112 },
          { name: "METROPOLIS II", p1: 176, p2: 112 },
          { name: "MODERN TIMES", p1: 64, p2: 112 },
          { name: "MOUNTAIN SHRINE", p1: 80, p2: 113 },
          { name: "PRELIMINARY FACE-OFF", p1: 96, p2: 112 },
          { name: "PRELIMINARY MATCH THEME", p1: 208, p2: 113 },
          { name: "PRIEST SETO THEME", p1: 64, p2: 114 },
          { name: "SEA SHRINE", p1: 16, p2: 113 },
          { name: "SETO KAIBA 3D BATTLE THEME", p1: 144, p2: 114 },
          { name: "SETO KAIBA FACE-OFF", p1: 128, p2: 112 },
          { name: "SETO KAIBA THEME", p1: 240, p2: 113 },
          { name: "SETO'S BETRAYAL", p1: 128, p2: 113 },
          { name: "SIMON MURAN", p1: 192, p2: 112 },
          { name: "TOURNAMENT ANNOUNCEMENT", p1: 48, p2: 112 },
          { name: "VALLEY OF THE KINGS", p1: 0, p2: 113 },
          { name: "VAST SHRINE", p1: 96, p2: 113 },
          { name: "LIBRARY MENU", p1: 208, p2: 114 },
          { name: "WIN OST", p1: 224, p2: 114 },
          { name: "LOSE OST", p1: 240, p2: 114 },
          { name: "GAME OVER", p1: 0, p2: 115 },
          { name: "EXODIA I", p1: 16, p2: 115 },
          { name: "EPILOGUE", p1: 32, p2: 115 },
          { name: "ENDING", p1: 42, p2: 115 },
          { name: "TOWN PLAZA FESTIVAL", p1: 64, p2: 115 },
          { name: "PASSWORD MENU", p1: 80, p2: 115 },
          { name: "MILLENIUM ITEM FOUND", p1: 96, p2: 115 },
          { name: "FORBIDDEN RUINS", p1: 112, p2: 115 },
          { name: "SIMON MURAN", p1: 128, p2: 115 },
        ],
        c = [
          { name: "LIGHT IN", param: "91" },
          { name: "LIGHT OUT", param: "90" },
          { name: "DARK IN", param: "A1" },
          { name: "DARK OUT", param: "A0" },
        ],
        l = [
          { name: "EARTHQUAKE", param: "2700" },
          { name: "NOOOOOOO!!", param: "2B00" },
          { name: "STEPS", param: "0380" },
          { name: "BROKEN PUZZLE", param: "2A00" },
          { name: "ITEM TO CARD CONVERSION", param: "2D00" },
          { name: "WIND", param: "0280" },
          { name: "DOORS OPEN", param: "0080" },
          { name: "OPEN TOMB", param: "2E00" },
          { name: "ITEMS ON RESONANCE", param: "0180" },
          { name: "TWISTER (HEISHIN CONVERSION)", param: "2C00" },
          { name: "FIRE (HEISHIN BURNS)", param: "2800" },
        ],
        u = [
          { name: "FAST", param: "00" },
          { name: "MEDIUM", param: "82" },
          { name: "SLOW", param: "83" },
        ];
    },
    "572b": function (t, e, a) {
      "use strict";
      var n = a("d8e9"),
        s = a.n(n);
      s.a;
    },
    "5e6c": function (t, e, a) {
      "use strict";
      (a("8e6e"), a("7f7f"), a("f559"), a("28a5"), a("a481"));
      var n = a("75fc"),
        s =
          (a("8615"),
          a("456d"),
          a("7514"),
          a("6b54"),
          a("ac6a"),
          a("5df3"),
          a("4f7f"),
          a("bd86")),
        r = a("5645");
      function i(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function o(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? i(a, !0).forEach(function (e) {
                Object(s["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : i(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      e["a"] = {
        data: function () {
          return { slusToolsRoseta: r["d"] };
        },
        methods: {
          setRoseta: function (t) {
            this.$set(this, "slusToolsRoseta", t);
          },
          getCardInfo: function (t) {
            var e =
                arguments.length > 1 && void 0 !== arguments[1]
                  ? arguments[1]
                  : {},
              a = o(
                {
                  desde: 1,
                  hasta: 722,
                  offset: 1859584,
                  isComplete: !1,
                  includeDescription: !1,
                  includeBytes: !1,
                  parseDescription: !1,
                },
                e,
              ),
              n = a.desde,
              s = a.hasta,
              r = a.offset,
              i = [],
              c = [];
            a.includeDescription &&
              a.parseDescription &&
              (c = this.readSpecialDescriptions(t, a.parseDescription));
            for (var l = n; l < s + 1; l++) {
              var u = 2 * l,
                d = 1 + 2 * l,
                h = t.getUint8(r + u, !0),
                p = t.getUint8(r + d, !0),
                f = h + 256 * p - 22528,
                m = {},
                g = "";
              (l >= 1 &&
                l <= 722 &&
                ((m = this.readValues(t, l)),
                a.includeDescription &&
                  (g = this.readDescription(t, l, a.parseDescription, c))),
                l < s + 1 &&
                  i.push({
                    name: this.readName(t, f + r, a.includeBytes),
                    id: i.length + 1,
                    data: m,
                    description: g,
                  }));
            }
            return i;
          },
          readName: function (t, e) {
            var a =
                arguments.length > 2 && void 0 !== arguments[2] && arguments[2],
              n = 0,
              s = "",
              r = this.getColor(0),
              i = 0,
              o = [];
            while (n < 255 && i < 50)
              ((n = t.getUint8(e + i, !0)),
                o.push(n),
                this.slusToolsRoseta["l" + n]
                  ? (s += this.slusToolsRoseta["l" + n])
                  : n < 255 &&
                    248 == n &&
                    ((n = t.getUint8(e + i + 2, !0)),
                    o.push(n),
                    (r = this.getColor(n)),
                    i++,
                    i++),
                i++);
            return {
              color: r,
              text: s,
              length: s.trim().length,
              offset: e,
              raw: a ? o : [],
            };
          },
          readValues: function (t, e) {
            var a =
                arguments.length > 2 && void 0 !== arguments[2]
                  ? arguments[2]
                  : 1854016,
              n =
                arguments.length > 3 && void 0 !== arguments[3]
                  ? arguments[3]
                  : 1858355,
              s = t.getUint8(a + 4 * e, !0),
              r = t.getUint8(a + 4 * e + 1, !0),
              i = t.getUint8(a + 4 * e + 2, !0),
              o = t.getUint8(a + 4 * e + 3, !0),
              c = s + 256 * (1 & r),
              l = (254 & r) / 2 + 128 * (3 & i),
              u = (60 & i) / 4,
              d = (192 & i) / 64 + 4 * (3 & o),
              h = (252 & o) / 4,
              p = t.getUint8(n + e - 1, !0),
              f = (240 & p) / 16,
              m = 15 & p;
            return {
              atk: 10 * c,
              def: 10 * l,
              st1: d,
              st2: u,
              type: h,
              level: m,
              attr: f,
            };
          },
          getColor: function (t) {
            var e = { color: "white", id: t };
            switch (t) {
              case 0:
                e.color = "white";
                break;
              case 1:
                e.color = "#EFEF00";
                break;
              case 2:
                e.color = "#849CFF";
                break;
              case 3:
                e.color = "#52D600";
                break;
              case 4:
                e.color = "#8C8C8C";
                break;
              case 5:
                e.color = "#E79410";
                break;
              case 6:
                e.color = "#FF0000";
                break;
              case 7:
                e.color = "#BD00BD";
                break;
              case 19:
                e.color = "white";
                break;
              default:
                e.color = "white";
                break;
            }
            return e;
          },
          readDescription: function (t, e) {
            var a =
                arguments.length > 2 && void 0 !== arguments[2] && arguments[2],
              n =
                arguments.length > 3 && void 0 !== arguments[3]
                  ? arguments[3]
                  : [],
              s = 1772032,
              r = 2 * e,
              i = 1 + 2 * e,
              o = t.getUint8(s + r, !0),
              c = t.getUint8(s + i, !0),
              l = s + o + 256 * c - 512;
            return this.readDescriptionText(t, l, a, n);
          },
          readSpecialDescriptions: function (t) {
            for (
              var e =
                  !(arguments.length > 1 && void 0 !== arguments[1]) ||
                  arguments[1],
                a = 1772032,
                n = new Set(),
                s = [],
                r = 1;
              r <= 722;
              r++
            ) {
              var i = 2 * r,
                o = 1 + 2 * r,
                c = t.getUint8(a + i, !0),
                l = t.getUint8(a + o, !0),
                u = a + c + 256 * l - 512,
                d = 0,
                h = 0;
              while (d < 255 && h < 200) {
                if (((d = t.getUint8(u + h, !0)), 248 === d)) h += 2;
                else if (252 === d) {
                  var p = t.getUint8(u + h + 1, !0),
                    f = t.getUint8(u + h + 2, !0),
                    m = a + p + 256 * f - 512;
                  (n.has(m) ||
                    (n.add(m),
                    s.push({
                      id: s.length,
                      description: this.readDescriptionText(t, m, e),
                      code: p + 256 * f,
                    })),
                    (h += 2));
                }
                h++;
              }
            }
            return s;
          },
          readDescriptionText: function (t, e) {
            var a =
                arguments.length > 2 && void 0 !== arguments[2] && arguments[2],
              n =
                arguments.length > 3 && void 0 !== arguments[3]
                  ? arguments[3]
                  : [],
              s = 0,
              r = "",
              i = "",
              o = [],
              c = 0;
            while (s < 255 && c < 200) {
              if (((s = t.getUint8(e + c, !0)), this.slusToolsRoseta["l" + s]))
                ((r += this.slusToolsRoseta["l" + s]),
                  (i += this.slusToolsRoseta["l" + s]));
              else if (s < 255) {
                if (248 == s) {
                  var l = t.getUint8(e + c + 1, !0),
                    u = t.getUint8(e + c + 2, !0);
                  (11 == l &&
                    (i +=
                      "¡" + ("00" + u.toString(16)).slice(-2).toUpperCase()),
                    10 == l &&
                      (i +=
                        "¿" + ("00" + u.toString(16)).slice(-2).toUpperCase()),
                    c++,
                    c++);
                }
                (252 == s &&
                  (function () {
                    var a = t.getUint8(e + c + 1, !0),
                      s = t.getUint8(e + c + 2, !0),
                      r = a + 256 * s,
                      o = n.find(function (t) {
                        return t.code === r;
                      }),
                      l = o ? o.id : 0;
                    ((i +=
                      "|" + ("00" + l.toString(16)).slice(-2).toUpperCase()),
                      (c += 2));
                  })(),
                  254 == s && ((r += " "), o.push(i), (i = "")));
              }
              c++;
            }
            return ("" != i && o.push(i), a ? o : r);
          },
          writeDescriptionParsed: function (t, e) {
            var a =
                arguments.length > 2 && void 0 !== arguments[2] && arguments[2],
              s =
                arguments.length > 3 && void 0 !== arguments[3]
                  ? arguments[3]
                  : [];
            if (722 != e.length) return !1;
            var r = 1772032,
              i = 2548;
            (t.setUint16(r, i, !0), i++);
            var o = {};
            s.forEach(function (t) {
              ((o[t.id] = i),
                t.description.forEach(function (t) {
                  i += t.trim().length + 1;
                }),
                0 == t.description.length && i++);
            });
            var c = [];
            if (
              (c.push(i),
              e.forEach(function (t) {
                (t.description.forEach(function (t) {
                  i += t.trim().length + 1;
                }),
                  0 == t.description.length && i++,
                  c.push(i));
              }),
              a)
            )
              return i;
            if (i > parseInt("FFFF", 16)) return !1;
            for (var l = 0; l < 722; l++)
              t.setUint16(r + 2 * (l + 1), c[l], !0);
            var u = Object.keys(this.slusToolsRoseta),
              d = Object.values(this.slusToolsRoseta),
              h = 1774068;
            return (
              t.setUint8(h, parseInt("FF", 16), !0),
              s.forEach(function (e) {
                var a = e.description.length,
                  s = 0;
                (e.description.forEach(function (r, i) {
                  var c = Object(n["a"])(
                      r.trim().matchAll(/[¡¿][0-9A-Fa-f]{2}/g),
                    ),
                    l = [];
                  c.forEach(function (t, e) {
                    l.push({ texto: t[0], index: t.index - 3 * e });
                  });
                  var p = r.trim().replace(/[¡¿][0-9A-Fa-f]{2}/g, ""),
                    f = p.split("");
                  f.forEach(function (a, n) {
                    var r = l.filter(function (t) {
                      return t.index == n;
                    });
                    r.length > 0 &&
                      r.forEach(function (a) {
                        var n = parseInt(a.texto.substring(1, 3), 16);
                        (t.setUint8(h + o[e.id] - 2548 + s, 248, !0),
                          s++,
                          a.texto.startsWith("¡")
                            ? t.setUint8(h + o[e.id] - 2548 + s, 11, !0)
                            : t.setUint8(h + o[e.id] - 2548 + s, 10, !0),
                          s++,
                          t.setUint8(h + o[e.id] - 2548 + s, n, !0),
                          s++);
                      });
                    var i = d.indexOf(a),
                      c = i > -1 ? parseInt("" + u[i].split("l")[1]) : 0;
                    (t.setUint8(h + o[e.id] - 2548 + s, c, !0), s++);
                  });
                  var m = l.filter(function (t) {
                    return t.index == f.length;
                  });
                  (m.length > 0 &&
                    m.forEach(function (a) {
                      var n = parseInt(a.texto.substring(1, 3), 16);
                      (t.setUint8(h + o[e.id] - 2548 + s, 248, !0),
                        s++,
                        a.texto.startsWith("¡")
                          ? t.setUint8(h + o[e.id] - 2548 + s, 11, !0)
                          : t.setUint8(h + o[e.id] - 2548 + s, 10, !0),
                        s++,
                        t.setUint8(h + o[e.id] - 2548 + s, n, !0),
                        s++);
                    }),
                    i == a - 1
                      ? t.setUint8(
                          h + o[e.id] - 2548 + s,
                          parseInt("FF", 16),
                          !0,
                        )
                      : t.setUint8(
                          h + o[e.id] - 2548 + s,
                          parseInt("FE", 16),
                          !0,
                        ),
                    s++);
                }),
                  0 == e.description.length &&
                    t.setUint8(h + o[e.id] - 2548, parseInt("FF", 16), !0));
              }),
              e.forEach(function (e, a) {
                var s = e.description.length,
                  r = 0;
                (e.description.forEach(function (e, i) {
                  var l = Object(n["a"])(
                      e.trim().matchAll(/[¡¿|][0-9A-Fa-f]{2}/g),
                    ),
                    p = [];
                  l.forEach(function (t, e) {
                    p.push({ texto: t[0], index: t.index - 3 * e });
                  });
                  var f = e.trim().replace(/[¡¿|][0-9A-Fa-f]{2}/g, ""),
                    m = f.split("");
                  m.forEach(function (e, n) {
                    var s = p.filter(function (t) {
                      return t.index == n;
                    });
                    s.length > 0 &&
                      s.forEach(function (e) {
                        var n = parseInt(e.texto.substring(1, 3), 16);
                        if (e.texto.startsWith("|")) {
                          (t.setUint8(h + c[a] - 2548 + r, 252, !0), r++);
                          var s = o[n] || 0,
                            i = s % 256,
                            l = Math.floor(s / 256);
                          (t.setUint8(h + c[a] - 2548 + r, i, !0),
                            r++,
                            t.setUint8(h + c[a] - 2548 + r, l, !0),
                            r++);
                        } else
                          (t.setUint8(h + c[a] - 2548 + r, 248, !0),
                            r++,
                            e.texto.startsWith("¡")
                              ? t.setUint8(h + c[a] - 2548 + r, 11, !0)
                              : t.setUint8(h + c[a] - 2548 + r, 10, !0),
                            r++,
                            t.setUint8(h + c[a] - 2548 + r, n, !0),
                            r++);
                      });
                    var i = d.indexOf(e),
                      l = i > -1 ? parseInt("" + u[i].split("l")[1]) : 0;
                    (t.setUint8(h + c[a] - 2548 + r, l, !0), r++);
                  });
                  var g = p.filter(function (t) {
                    return t.index == m.length;
                  });
                  (g.length > 0 &&
                    g.forEach(function (e) {
                      var n = parseInt(e.texto.substring(1, 3), 16);
                      if (e.texto.startsWith("|")) {
                        (t.setUint8(h + c[a] - 2548 + r, 252, !0), r++);
                        var s = o[n] || 0,
                          i = s % 256,
                          l = Math.floor(s / 256);
                        (t.setUint8(h + c[a] - 2548 + r, i, !0),
                          r++,
                          t.setUint8(h + c[a] - 2548 + r, l, !0),
                          r++);
                      } else
                        (t.setUint8(h + c[a] - 2548 + r, 248, !0),
                          r++,
                          e.texto.startsWith("¡")
                            ? t.setUint8(h + c[a] - 2548 + r, 11, !0)
                            : t.setUint8(h + c[a] - 2548 + r, 10, !0),
                          r++,
                          t.setUint8(h + c[a] - 2548 + r, n, !0),
                          r++);
                    }),
                    i == s - 1
                      ? t.setUint8(h + c[a] - 2548 + r, parseInt("FF", 16), !0)
                      : t.setUint8(h + c[a] - 2548 + r, parseInt("FE", 16), !0),
                    r++);
                }),
                  0 == e.description.length &&
                    t.setUint8(h + c[a] - 2548, parseInt("FF", 16), !0));
              }),
              !0
            );
          },
          writeAllCardValues: function (t, e) {
            var a = this;
            e.forEach(function (e) {
              var n = e.id,
                s = Math.floor((e.data.atk % 5511) / 10),
                r = Math.floor((e.data.def % 5511) / 10),
                i = e.data.st1,
                o = e.data.st2,
                c = e.data.type,
                l = e.data.level,
                u = e.data.attr;
              a.writeValuesOnSingleCard(t, n, s, r, i, o, c, l, u);
            });
          },
          writeValuesOnSingleCard: function (t, e, a, n, s, r, i, o, c) {
            var l = 1854016,
              u = 1858355,
              d = a % 256,
              h = (n % 128) * 2 + Math.floor(a / 256),
              p = (s % 4) * 64 + 4 * r + Math.floor(n / 128),
              f = 4 * i + Math.floor(s / 4);
            (t.setUint8(l + 4 * e, d),
              t.setUint8(l + 4 * e + 1, h),
              t.setUint8(l + 4 * e + 2, p),
              t.setUint8(l + 4 * e + 3, f));
            var m = 16 * c + o;
            t.setUint8(u + e - 1, m);
          },
          writeAllNamesOnSlus: function (t, e, a, s, r) {
            var i =
                arguments.length > 5 && void 0 !== arguments[5] && arguments[5],
              o = [].concat(
                Object(n["a"])(e),
                Object(n["a"])(a),
                Object(n["a"])(s),
                Object(n["a"])(r),
              ),
              c = 1859584,
              l = 24576;
            t.setUint16(c, l, !0);
            var u = [];
            if (
              (u.push(l),
              l++,
              o.forEach(function (t) {
                var e = t.name.color ? t.name.color.id : 0,
                  a = t.name.text.trim().length + (0 == e ? 0 : 3) + 1,
                  n = l;
                (l + a >= 35533 && l < 35533 && (n = 35534),
                  l + a >= 36250 && l < 36250 && (n = 37376),
                  (l = n),
                  u.push(l),
                  (l += a));
              }),
              i)
            )
              return l;
            if (l >= parseInt("A004", 16)) return !1;
            var d = [];
            d.push({ name: "", p: u[0], color: 0 });
            for (var h = 1; h < 723; h++)
              d.push({
                name: e[h - 1].name.text,
                p: u[h],
                color: e[h - 1].name.color.id,
              });
            for (var p = 0; p < 45; p++)
              d.push({ name: "", p: 24576, color: 0 });
            for (var f = 723; f < 762; f++)
              d.push({ name: o[f - 1].name.text, p: u[f], color: 0 });
            for (var m = 0; m < 1; m++)
              d.push({ name: o[722].name.text, p: u[723], color: 0 });
            for (var g = 762; g < 802; g++)
              d.push({ name: o[g - 1].name.text, p: u[g], color: 0 });
            d.forEach(function (e, a) {
              t.setUint16(c + 2 * a, e.p, !0);
            });
            for (var v = 864; v < 1024; v++)
              t.setUint16(c + 2 * v, d[768].p, !0);
            var b = Object.keys(this.slusToolsRoseta),
              w = Object.values(this.slusToolsRoseta),
              y = 1861632;
            return (
              t.setUint8(y, parseInt("FF", 16), !0),
              d.forEach(function (e, a) {
                var n = e.name.trim().split(""),
                  s = 0;
                (e.color > 0 &&
                  (t.setUint8(y + e.p - 24576 + s, 248, !0),
                  t.setUint8(y + e.p - 24576 + s + 1, 10, !0),
                  t.setUint8(y + e.p - 24576 + s + 2, e.color, !0),
                  (s += 3)),
                  n.forEach(function (a) {
                    var n = w.indexOf(a),
                      r = n > -1 ? parseInt("" + b[n].split("l")[1]) : 0;
                    (t.setUint8(y + e.p - 24576 + s, r, !0), s++);
                  }),
                  t.setUint8(y + e.p - 24576 + s, parseInt("FF", 16), !0),
                  s++);
              }),
              !0
            );
          },
        },
      };
    },
    6504: function (t, e, a) {},
    "669c": function (t, e, a) {},
    6730: function (t, e) {
      var a = "en",
        n = "en";
      switch (
        (localStorage.getItem("Len") && (a = localStorage.getItem("Len")), a)
      ) {
        case "pt":
          n = "pt-br";
          break;
        case "vn":
          n = "vi";
          break;
        default:
          n = a;
          break;
      }
      moment && moment.locale(n);
    },
    "69e0": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", [
            a("div", { staticClass: "mini-banner padre" }, [
              a("div", { staticClass: "top-bar" }),
              a("span", { staticClass: "hijo no-text" }, [t._v("TEA")]),
              a(
                "span",
                {
                  staticClass: "hijo",
                  on: {
                    click: function (e) {
                      return t.goHome();
                    },
                  },
                },
                [a("font-awesome-icon", { attrs: { icon: "arrow-left" } })],
                1,
              ),
              t.element
                ? a(
                    "span",
                    {
                      staticClass: "hijo",
                      on: {
                        click: function (e) {
                          return t.sidenav.open();
                        },
                      },
                    },
                    [a("font-awesome-icon", { attrs: { icon: "bars" } })],
                    1,
                  )
                : t._e(),
            ]),
            t.element
              ? a(
                  "ul",
                  {
                    staticClass: "sidenav scrpe bg-fiber",
                    attrs: { id: "regular-side" },
                  },
                  [
                    a("li", { staticClass: "sidenav-head no-text" }, [
                      t._v("#TEAONLINE"),
                    ]),
                    a(
                      "li",
                      [
                        a(
                          t.element,
                          t._b(
                            { tag: "component" },
                            "component",
                            t.propsElement,
                            !1,
                          ),
                        ),
                      ],
                      1,
                    ),
                  ],
                )
              : t._e(),
          ]);
        },
        s = [],
        r = {
          name: "regularSide",
          data: function () {
            return { sidenav: null };
          },
          props: {
            element: { type: Object, default: null },
            propsElement: {
              type: Object,
              default: function () {
                return {};
              },
            },
          },
          methods: {
            goto: function (t) {
              location.href = t;
            },
            goHome: function () {
              this.goto("/extend");
            },
          },
          mounted: function () {
            this.$nextTick(function () {
              this.$nextTick(function () {
                if (this.element) {
                  var t = document.querySelectorAll(".sidenav");
                  M.Sidenav.init(t, {});
                  this.sidenav = M.Sidenav.getInstance(
                    document.getElementById("regular-side"),
                  );
                }
              });
            });
          },
        },
        i = r,
        o = (a("e50d"), a("2877")),
        c = Object(o["a"])(i, n, s, !1, null, "7bc8d7b8", null);
      e["a"] = c.exports;
    },
    "6a66": function (t, e, a) {},
    "70b8": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", { staticClass: "breadcrum" }, [
            a(
              "h4",
              { staticClass: "germania izquierda white-text sh-t-2" },
              [
                t._l(t.tags, function (e, n) {
                  return [
                    a("span", { key: "it-1-" + n }, [t._v(t._s(e))]),
                    n + 1 < t.tags.length
                      ? a(
                          "span",
                          { key: "it-2-" + n },
                          [
                            t._v("\n                 \n                "),
                            a("font-awesome-icon", {
                              attrs: { icon: "angle-right" },
                            }),
                            t._v("\n                 \n            "),
                          ],
                          1,
                        )
                      : t._e(),
                  ];
                }),
              ],
              2,
            ),
          ]);
        },
        s = [],
        r =
          (a("ac6a"),
          a("28a5"),
          {
            name: "BreadCrum",
            data: function () {
              return { tags: [] };
            },
            props: { inicio: { type: String, default: "extend" } },
            created: function () {
              var t = this,
                e = document.location.href.split("?");
              e = e[0].split("/");
              var a = !1;
              ((this.tags = []),
                e.forEach(function (e) {
                  (e == t.inicio && (a = !0), a && t.tags.push(e));
                }));
            },
          }),
        i = r,
        o = a("2877"),
        c = Object(o["a"])(i, n, s, !1, null, null, null);
      e["a"] = c.exports;
    },
    "716a": function (t, e, a) {
      "use strict";
      var n = a("6504"),
        s = a.n(n);
      s.a;
    },
    "757c": function (t, e, a) {},
    7906: function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", [
            a(
              "div",
              {
                directives: [
                  {
                    name: "show",
                    rawName: "v-show",
                    value: t.alertRank > 0,
                    expression: "alertRank > 0",
                  },
                ],
              },
              [
                a(
                  "p",
                  {
                    class: {
                      "c-green": 1 == t.alertRank,
                      "c-red": 2 == t.alertRank,
                      "c-orange": 3 == t.alertRank,
                      shadow: !t.hideShadow,
                    },
                    attrs: { alert: "" },
                  },
                  [t._t("default")],
                  2,
                ),
              ],
            ),
          ]);
        },
        s = [],
        r =
          (a("c5f6"),
          {
            name: "AlertBanner",
            props: {
              alertRank: { default: 0, type: Number },
              hideShadow: { default: !1, type: Boolean },
            },
          }),
        i = r,
        o = (a("bf8f"), a("2877")),
        c = Object(o["a"])(i, n, s, !1, null, "dab7c2cc", null);
      e["a"] = c.exports;
    },
    "79c9": function (t, e, a) {},
    "802b": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", { staticClass: "check" });
        },
        s = [],
        r = (a("8e6e"), a("ac6a"), a("456d"), a("96cf"), a("3b8d")),
        i = a("bd86"),
        o = a("2f62"),
        c = a("bc3a"),
        l = a.n(c),
        u = a("f8eb");
      function d(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function h(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? d(a, !0).forEach(function (e) {
                Object(i["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : d(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      var p = {
          name: "check",
          computed: h(
            {},
            Object(o["c"])(["api", "isLoading", "user", "things", "version"]),
          ),
          mixins: [u["a"]],
          methods: h(
            {},
            Object(o["b"])(["load", "setThings", "chlo", "initAxios"]),
            {
              request: (function () {
                var t = Object(r["a"])(
                  regeneratorRuntime.mark(function t() {
                    var e = this;
                    return regeneratorRuntime.wrap(
                      function (t) {
                        while (1)
                          switch ((t.prev = t.next)) {
                            case 0:
                              (this.setThings(this.user.id),
                                l()({
                                  method: "POST",
                                  url:
                                    this.api +
                                    "api/v2/users/validate?v=" +
                                    this.version.numero,
                                  headers: h(
                                    {
                                      "Content-Type": "application/json",
                                      Accept:
                                        "application/json, text/plain, */*",
                                    },
                                    this.things,
                                  ),
                                })
                                  .then(function (t) {
                                    t.data.ok;
                                  })
                                  .catch(function (t) {
                                    (M.toast({
                                      html: "Session is over, please login again!",
                                    }),
                                      e.check401(t));
                                  }));
                            case 2:
                            case "end":
                              return t.stop();
                          }
                      },
                      t,
                      this,
                    );
                  }),
                );
                function e() {
                  return t.apply(this, arguments);
                }
                return e;
              })(),
            },
          ),
          created: function () {
            if (localStorage.getItem("user")) {
              var t = JSON.parse(localStorage.getItem("user"));
              this.chlo({ key: "user", value: t });
            } else this.goto("/extend/user/register");
            (this.initAxios(), this.request());
          },
        },
        f = p,
        m = a("2877"),
        g = Object(m["a"])(f, n, s, !1, null, null, null);
      e["a"] = g.exports;
    },
    "877b": function (t, e, a) {},
    8780: function (t, e, a) {},
    8969: function (t, e, a) {
      "use strict";
      (a("8e6e"), a("ac6a"), a("456d"));
      var n = a("bd86"),
        s = (a("28a5"), a("2b0e")),
        r = a("2f62"),
        i = a("6821f"),
        o = a.n(i),
        c = a("bc3a"),
        l = a.n(c);
      function u(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function d(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? u(a, !0).forEach(function (e) {
                Object(n["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : u(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      (s["a"].use(r["a"]),
        (e["a"] = new r["a"].Store({
          state: {
            loadgen: !1,
            indice: 1,
            api: "https://www.basededatostea.xyz/",
            base: "https://basededatostea.xyz/",
            version: {
              abreviatura: "ori",
              directorio: "original/",
              id: "1",
              numero: "1",
              nombre: "Original",
            },
            carta: {
              Numero: 0,
              Nombre: "",
              Atk: "",
              Def: "",
              St1: "",
              St2: "",
              Tipo: "",
              Password: "",
              Precio: "",
              Comentario: "",
              Color: 0,
              prov: !0,
            },
            oponenteSel: { id: 0, nombre: "", prov: !0 },
            colors: [
              "white-text",
              "yellow-text",
              "blue-text text-accent-4",
              "purple-text text-lighten-1",
              "blue-grey-text text-llighten-1",
              "orange-text text-accent-2",
              "red-text",
              "light-green-text text-accent-3",
            ],
            uloads: {
              hnames: !1,
              hversion: !1,
              hnews: !1,
              hnoti: !1,
              hop: !1,
              hleq: !1,
              rct: !1,
              rop: !1,
              rini: !1,
              req: !1,
              rrit: !1,
              rfus: !1,
            },
            lhversion: !1,
            things: {},
            tg: "De_un_golpe abrí la_puerta, y_con suave batir de_alas, entró un_majestuoso cuervo de_los_santos días idos. Sin asomos de_reverencia, ni_un_instante quedo; y_con_aires de_gran_señor o_de_gran_dama fue_a_posarse en_el_busto de_Palas, sobre el_dintel de_mi_puerta. Posado, inmóvil, y_nada_más. Entonces, este pájaro de_ébano cambió mis_tristes fantasías en_una_sonrisa con_el_grave y_severo decoro del_aspecto de_que_se_revestía. Aun_con_tu_cresta cercenada y_mocha -le_dije-, no_serás un_cobarde, hórrido cuervo_vetusto y_amenazador. Evadido de_la_ribera nocturna. ¡Dime cuál es_tu_nombre en_la_ribera de_la_Noche Plutónica! Y_el_Cuervo dijo: Nunca_más.",
            panel: 1,
            atributes: [
              "Light",
              "Dark",
              "Earth",
              "Water",
              "Fire",
              "Wind",
              "Magic",
              "Trap",
            ],
            log: { texto: "Noticias", id: "0", fecha: "" },
            token: "",
            isLoading: !1,
            cancelToken: null,
            source: null,
            countReset: 0,
            countRequest: 0,
            user: {},
            likesNumber: 0,
            tkn: "",
            notifications: [],
            appModal: { isOpen: !1, mode: "regular", title: "" },
          },
          mutations: {
            cambiar: function (t, e) {
              t.indice = e;
            },
            cversion: function (t, e) {
              ((t.version = e),
                sessionStorage.removeItem("oponentes"),
                sessionStorage.removeItem("equipos"),
                localStorage.setItem("version", JSON.stringify(t.version)));
            },
            cload: function (t, e) {
              t.loadgen = e;
            },
            ccarta: function (t, e) {
              ((t.carta = e),
                localStorage.setItem("carta", JSON.stringify(t.carta)));
            },
            coponente: function (t, e) {
              ((t.oponenteSel = e),
                localStorage.setItem(
                  "oponente",
                  JSON.stringify(t.oponenteSel),
                ));
            },
            cu: function (t, e) {
              t.uloads[e.key] = e.value;
            },
            chlo: function (t, e) {
              t[e.key] = e.value;
            },
            setThings: function (t) {
              var e =
                  arguments.length > 1 && void 0 !== arguments[1]
                    ? arguments[1]
                    : "",
                a = new Date(),
                n = a.getHours() + ":" + a.getMinutes() + ":" + a.getSeconds();
              t.things = {
                hash: o()(
                  "" + e + n + t.tg.split(" ")[a.getSeconds()] + t.version.id,
                ),
                hora: n,
                dif: a.getTimezoneOffset(),
                Authorization: "Basic " + t.token,
              };
            },
            load: function (t, e) {
              t.isLoading = e;
            },
            initAxios: function (t) {
              ((t.cancelToken = l.a.CancelToken),
                (t.source = t.cancelToken.source()));
            },
            setToken: function (t, e) {
              t.token = e;
            },
            reset: function (t) {
              t.countReset += 1;
            },
            complete: function (t, e) {
              (e ? (t.countRequest -= 1) : (t.countRequest += 1),
                0 == t.countRequest ? (t.isLoading = !1) : (t.isLoading = !0));
            },
            pushNotification: function (t, e) {
              var a = Date.now() + Math.random();
              t.notifications.push({
                id: a,
                type: e.type || "info",
                title: e.title || "",
                message: e.message || "",
                duration: e.duration || 4e3,
              });
            },
            removeNotification: function (t, e) {
              t.notifications = t.notifications.filter(function (t) {
                return t.id !== e;
              });
            },
            openModal: function (t) {
              var e =
                arguments.length > 1 && void 0 !== arguments[1]
                  ? arguments[1]
                  : {};
              t.appModal = {
                isOpen: !0,
                mode: e.mode || "regular",
                title: e.title || "",
              };
            },
            closeModal: function (t) {
              t.appModal = d({}, t.appModal, { isOpen: !1 });
            },
          },
          actions: {},
        })));
    },
    "99d5": function (t, e, a) {},
    "9e7a": function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", [
            a(
              "div",
              {
                directives: [
                  {
                    name: "show",
                    rawName: "v-show",
                    value: t.isloading,
                    expression: "isloading",
                  },
                ],
                attrs: { bcourtain: "" },
              },
              [
                a("div"),
                a(
                  "h5",
                  { attrs: { holder: "" } },
                  [
                    a("font-awesome-icon", {
                      attrs: { icon: "cog", spin: "" },
                    }),
                    t._v(" " + t._s(t.$t("loading")) + "..."),
                  ],
                  1,
                ),
              ],
            ),
          ]);
        },
        s = [],
        r = {
          name: "FullLoader",
          props: { isloading: { type: Boolean, default: !1 } },
        },
        i = r,
        o = (a("4a23"), a("2877")),
        c = Object(o["a"])(i, n, s, !1, null, "73c1e670", null);
      e["a"] = c.exports;
    },
    a240: function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", { staticClass: "filereader" }, [
            a("div", { staticClass: "row" }, [
              a("div", { staticClass: "col s12 m12" }, [
                a("div", { staticClass: "memoryName roboto" }, [
                  a(
                    "span",
                    {
                      staticClass: "manito fr-btn",
                      on: {
                        click: function (e) {
                          return t.search();
                        },
                      },
                    },
                    [
                      a("font-awesome-icon", { attrs: { icon: "search" } }),
                      t._v(
                        "\n                    " +
                          t._s(t.memoryName) +
                          "\n                ",
                      ),
                    ],
                    1,
                  ),
                ]),
              ]),
            ]),
            a("div", { staticClass: "row" }, [
              a(
                "div",
                {
                  directives: [
                    {
                      name: "show",
                      rawName: "v-show",
                      value: !1,
                      expression: "false",
                    },
                  ],
                  staticClass: "col s12",
                },
                [
                  a("input", {
                    attrs: { type: "file", id: t.id, accept: t.accepted },
                    on: {
                      change: function (e) {
                        return t.analizeMemory(e);
                      },
                    },
                  }),
                ],
              ),
            ]),
          ]);
        },
        s = [],
        r =
          (a("7f7f"),
          a("c5f6"),
          a("2f62"),
          {
            name: "FileReader",
            data: function () {
              return { formInput: null, reader: new FileReader(), file: null };
            },
            props: {
              accepted: { type: String, default: ".mcr,.mem,.mcd" },
              maxsize: { type: [String, Number], default: 2048e3 },
              minsize: { type: [String, Number], default: 0 },
              id: {
                type: [String, Number],
                default: function () {
                  return Date.now();
                },
              },
              text: { type: String, default: "selectyourslus" },
            },
            computed: {
              memoryName: function () {
                return null != this.file ? this.file.name : this.$t(this.text);
              },
            },
            methods: {
              search: function () {
                this.formInput.click();
              },
              analizeMemory: function (t) {
                var e = t.target;
                e.files &&
                  e.files[0] &&
                  (e.files[0].size <= this.maxsize &&
                  e.files[0].size >= this.minsize
                    ? ((this.file = e.files[0]),
                      this.reader.readAsArrayBuffer(this.file))
                    : alert("Wrong File Size!"));
              },
              reset: function () {
                ((this.formInput.value = ""),
                  /safari/i.test(navigator.userAgent) ||
                    ((this.formInput.type = ""),
                    (this.formInput.type = "file")));
              },
            },
            mounted: function () {
              var t = this;
              this.$nextTick(function () {
                ((t.formInput = document.getElementById(t.id)),
                  (t.reader.onload = function (e) {
                    var a = e.target.result,
                      n = new DataView(a);
                    (t.$emit("readed", n),
                      t.$emit("named", t.memoryName),
                      t.$emit("new:file", { name: t.memoryName, dataview: n }));
                  }));
              });
            },
          }),
        i = r,
        o = (a("3e8c"), a("2877")),
        c = Object(o["a"])(i, n, s, !1, null, "4f5b6d7c", null);
      e["a"] = c.exports;
    },
    ad69: function (t, e, a) {},
    b0fa: function (t, e, a) {},
    b2e2: function (t, e, a) {},
    b64e: function (t, e, a) {
      "use strict";
      var n = a("6a66"),
        s = a.n(n);
      s.a;
    },
    b85c: function (t, e, a) {},
    bf8f: function (t, e, a) {
      "use strict";
      var n = a("33ef"),
        s = a.n(n);
      s.a;
    },
    c17f: function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", [
            a("div", {
              staticClass: "black-courtain",
              class: { open: t.isOpen },
              on: {
                click: function (e) {
                  return t.close();
                },
              },
            }),
            a(
              "div",
              {
                staticClass: "modal-new",
                class: [t.isOpen ? "open" : "", t.mode],
              },
              [
                a("div", { staticClass: "modal-header" }, [
                  a("span", [t._v(t._s(t.title))]),
                  a(
                    "span",
                    {
                      on: {
                        click: function (e) {
                          return t.close();
                        },
                      },
                    },
                    [
                      a("font-awesome-icon", {
                        attrs: { icon: "window-close" },
                      }),
                    ],
                    1,
                  ),
                ]),
                a("div", { staticClass: "modal-body" }, [t._t("default")], 2),
              ],
            ),
          ]);
        },
        s = [],
        r = a("ecee"),
        i = a("c074");
      r["c"].add(i["hb"]);
      var o = {
          name: "Modal",
          data: function () {
            return { isOpen: !1 };
          },
          components: {},
          props: {
            mode: { type: String, default: "" },
            title: { type: String, default: "" },
          },
          methods: {
            open: function () {
              ((this.isOpen = !0), (document.body.style.overflow = "hidden"));
            },
            close: function () {
              ((this.isOpen = !1),
                (document.body.style.overflow = "auto"),
                this.$emit("modal:close", !0));
            },
          },
        },
        c = o,
        l = (a("f5cf"), a("2877")),
        u = Object(l["a"])(c, n, s, !1, null, "d43670d8", null);
      e["a"] = u.exports;
    },
    c3d7: function (t) {
      t.exports = {
        advaceDownloaded: "Avance descargado!",
        advaceUpdated: "Avance actualizado",
        agree: "De acuerdo",
        agregado: "agregado!",
        alreadyMailExist: "El correo esta en uso!",
        alreadyUserExist: "El nombre de usuario ya existe!",
        anuncios: "Anuncios",
        articulos: "Articulos",
        ataque: "Ataque",
        avatar: "Avatar",
        backups: "Respaldos",
        baseDeDatos: "Base de datos de Yugioh! Forbidden Memories y sus mods",
        basicData: "Datos Básicos",
        bestCards: "Mejor carta de la semana",
        blockCompatibility:
          "Este bloque es compatible con todas estas versiones",
        boughts: "Compradas",
        buscar: "Buscar",
        buscarCarta: "Busca una carta",
        campoLLeno: "El campo está lleno!",
        cardsOnChest: "Cartas en el chest",
        carta: "Carta",
        cartas: "cartas",
        Cartas: "Cartas",
        change: "Cambiar",
        chestRequirements: "Requerimientos de Chest",
        choiseAnotherMemory:
          "Busca otro archivo, esta memoria no tiene una partida de FM",
        choiseBlock: "Elige un bloque de la memorycard",
        choiseYourMemory: "Elige tu memorycard",
        chooseAvatar: "Elige un avatar",
        clasico: "Clásico",
        cockieMessage:
          "Este sitio usa cookies propias y de terceros para darta una experiencia personalizada, continuar usando el sitio supone su aceptación.",
        confirmAvatar: "Confirma tu avatar",
        consultar: "Consultar",
        corruptedData: "Datos corruptos!",
        createBackup: "Crear respaldo",
        createUserMsg: "Usuario creado!",
        data: "Datos",
        deck: "Deck",
        deckDe: "Deck de",
        deckInicial: "deck inicial",
        defensa: "Defensa",
        deIn: "Deck inicial",
        deleteAdvance: "Borrar avance",
        deleteAdvanceBody:
          "Esta acción borrará los datos de tu cuenta, todo tu avance será borrado",
        deleteBackup: "Borrar respaldo",
        deleteBackupBody:
          "Esta acción borrará el respaldo de tu cuenta, y no podrá ser recuperado",
        deleteGame: "Borrar juego",
        deleteGameBody:
          "Esta acción borrarátu juego de la lista de los últimos decks, y no podrá ser recuperado",
        deleteLocalData: "Borrar datos locales",
        deleteLocalDataBody:
          "Esta acción borrará los datos locales de este dispositivo, todas las cartas se desmarcarán",
        descripcionClasico:
          "Modo clásico, ahora mejorado para soportar más mods.",
        descripcionExtendido:
          "Version extendida, con mas características e información, además podrás crear una cuenta para acceder a más funciones",
        descripcionGuia: "Cartas, oponentes, equipos y más",
        descripcionHerramientas: "Utilitarios",
        descripcionIngresar: "Accede a tu cuenta",
        descripcionNoticias: "Anuncios, estadisticas y más",
        dowladAdvance: "Descargar avance",
        dowladAdvanceBody:
          "Esta acción reemplazará los datos locales de este dispositivo, todas las marcas de tus cartas serán reemplazadas por las guardadas en tu cuenta.",
        dropRate: "Drop Rate",
        edit: "Editar",
        editData: "Edita tus datos",
        ejemplos: "Ejemplos",
        elige: "Elige una versión de TEAONLINE",
        emptyBackups: "El usuario no tiene respaldos públicos para mostrar",
        emptyGames: "El usuario no tiene juegos para mostrar",
        equipCards: "Cartas de Equipo",
        equipos: "equipos",
        Equipos: "Equipos",
        equiposCompatibles: "Equipos compatibles",
        erasedLoacalData: "Datos locales borrados",
        estrella: "Estrella",
        extendido: "Extendido",
        fusion: "Fusion",
        fusionar: "Fusionar",
        fusiones: "fusiones",
        fusiones1: "Fusiones",
        fusiones2: "Fusiones con esta carta",
        fusionesM: "Fusiones",
        games: "Juegos",
        guiaCartas: "Guía de cartas",
        guiaDeckInicial: "Guía del deck inicial",
        guiaEquipos: "Guía de equipos",
        guiaFusiones: "Guía de Fusiones",
        guiaOponentes: "Guía de oponentes",
        guiaRituales: "Guía de Rituales",
        guias: "Guías",
        hasAccount: "Tienes una cuenta",
        Herramientas: "Herramientas",
        hideMemory: "Ocultar memorycard",
        hideMemoryBody:
          "Esta acción ocultará tu memorycard, nadie podrá descargarla",
        informacionNoDisponible: "La información no está disponible",
        ingresaNombre: "Ingresa el nombre o número de una carta",
        Ingresar: "Ingresar",
        lastname: "Apellido",
        later: "Quizas luego",
        latestSaves: "Últimos juegos de usuarios",
        lectorMemoria: "Lector de memorycard",
        listaAnunciosNoDisponible: "La lista de anuncios no está disponible",
        listaCartasNoDisponible: "La lista de cartas no está disponible",
        listaEquiposNoDisponibles: "La lista de equipos no está disponible",
        listaNoticiasNoDisponible: "La lista de noticias no está disponible",
        listaOponentesNoDisponible: "La lista de oponentes no está disponible",
        listaVersionesNoDisponible: "La lista de versiones no está disponible",
        loading: "Cargando",
        localData: "Datos locales",
        localMemoryEmpy: "Memoria local esta vacía",
        logout: "Salir",
        Mail: "Correo",
        mailDontExist: "El correo no está registrado",
        maillbl: "correo",
        makeFusion: "Hacer una fusión",
        makePublic: "Hacer público",
        makePublicBody:
          "Esta acción hara publica tu memorycard, todos podrán descargarla",
        mandatoryField: "Campo obligatorio",
        manoLLena: "La mano está llena!",
        marked: "Mostrar cartas marcadas",
        memory: "Memoria",
        memorycardReader: "Lector de memorycard",
        mensajeContacto:
          "Creaste un mod que debería estar en TEAONLINE? Envía un correo a:",
        newAvatarMsg: "Nuevo avatar seleccionado!",
        newPassword: "Nueva contraseña",
        newPasswordx2: "Repita la nueva contraseña",
        next: "Siguiente",
        no: "No",
        noAdvances: "No hay avances en tu cuenta",
        noBackups: "No tienes respaldos!",
        noGames: "No hay juegos guardados",
        nombre: "Nombre",
        Noticias: "Noticias",
        numero: "Número",
        numRows: "Número de registros",
        obtained: "Conseguido",
        oldPassword: "Antigüa contraseña",
        onLibrary: "En Library",
        oponente: "Oponente",
        oponentes: "oponentes",
        Oponentes: "Oponentes",
        oponentesDan: "Oponentes que dan la carta",
        oponentesUsan: "Oponentes que usan la carta",
        opponentDeckRate: "Deck rate de oponentes",
        options: "Opciones",
        page: "Página",
        password: "Contraseña",
        passwordlbl: "contraseña",
        Passwords: "Contraseñas",
        picture: "Imagen",
        precio: "Precio",
        previus: "Anterior",
        probabilidad: "Probabilidad",
        profile: "Perfil",
        pulsaBoton: "Presiona el boton para acceder a la guía",
        rango: "Rank",
        rankCalculator: "Rank Calculator",
        ranker: "Rank Calculator",
        rankMsg:
          "Cada acción en un duelo cambia tus puntos de duelo, cuando el duelo termina serás clasificado con un rango acorde a tus puntos finales. Esta herramienta calculará cual es el rango actual según las acciones que indiques.",
        register: "Registrar",
        repeatPassword: "Repite tu contraseña",
        resultado: "Resultado",
        ritualCards: "Cartas Ritual",
        rituales: "rituales",
        Rituales: "Rituales",
        rituales2: "Rituales con esta carta",
        saveData: "Save Data",
        searchYourMemory: "Busca tú memorycard",
        seleccionaEquipo: "Selecciona un equipo",
        seleccionaOponente: "Selecciona un oponente",
        selectYourData: "Selecciona tu save data",
        shareMsg: "Comparte tu avance! Crea un Respaldo y protege tu juego!",
        showOnlyType: "Mostrar solo el tipo",
        si: "Si",
        simulate: "Simular",
        simulatorInitial: "Simulador de Deck Inicial",
        sinResultados: "No hay resultados",
        specialConditions: "Condiciones Especiales",
        SupportKeepGoing: "Apoya a #TEAONLINE a seguir adelante!",
        supportThrough: "Respaldanos mediante",
        sure: "¿Estás seguro?",
        syncGame: "Sincronizar juego con datos locales",
        syncGameBody:
          "Esta acción reemplazará el avance de este dispositivo, pero no actualizará los datos en tu cuenta. Si deseas también actualizar los datos de tu cuenta ve a la sección de Datos locales.",
        tapClick: "Tap o Click en la fusión para colocarla en el campo",
        tea: "Todo está aquí!",
        text: "Texto",
        textoDeckInicial:
          "El deck inicial esta conformado por una determinada cantidad de cartas procedentes de 7 conjuntos de cartas, para en total conformar el deck de 40 cartas.",
        textoPanelFusion:
          "Simulador de fusiones para las cartas de la mano y el campo.",
        textoPanelInicial: "Conjunto de cartas para crear el deck inicial.",
        textoPanelPassword: "Código de cartas para comprar con estrellas.",
        textoPanelRitual: "Requerimientos para invocar cartas por ritual.",
        textoPanelTorre:
          "Drop del último duelo del modo de juego especial presente en algunos mods.",
        tipo: "Tipo",
        top10: "Top 10 - Cartas",
        torre: "Torre",
        txtNoRegister: "¿No estás registrado aún?",
        txtRegister: "Registrar",
        txtSendLogin: "Enviar",
        ultimaActualizacion: "Actualizado",
        ultimosDecks: "Últimos decks",
        uniqueCards: "Cartas únicas",
        updatePassword: "Actualizar contraseña",
        updateProfile: "Actualizar Perfil",
        uploadAdvance: "Subir avance",
        uploadAdvanceBody:
          "Esta acción reemplazará los datos en tu cuenta, todas tus cartas serán reemplazadas por los datos de este dispositivo y no podrán ser recuperados.",
        username: "Usuario",
        usernameLabel: "Username",
        validMailMsg: "Ingresa un correo válido",
        validPassword: "Contraseñas no coinciden",
        verMas: "Ver más",
        version: "Version",
        versiones: "Versiones",
        viewProfile: "Ver Perfil",
        volver: "Atrás",
        warningInitial:
          "Este mod no tiene conjuntos de cartas para formar el deck inicial, debes comprar cartas para construir tu deck.",
        warningRitual: "Esta versión no tiene rituales",
        warninTower: "Este mod no tiene modo Torre",
        welcomeToTea: "Bienvenido a TEAONLINE",
        wrongPassword: "Contraseña incorrecta",
        save: "salvar",
        selectyourwa: "seleccionar WA_MRG.MRG",
        selectyourimage: "Cargar Imagen",
      };
    },
    c75b: function (t, e, a) {},
    cc11: function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", { staticClass: "tool-presentation" }, [
            a(
              "div",
              { staticClass: "cover-list", class: { go: t.removeCover } },
              [
                a("div", { staticClass: "back-bar" }, [
                  a(
                    "div",
                    {
                      on: {
                        click: function (e) {
                          return t.goto("/extend/tools");
                        },
                      },
                    },
                    [a("font-awesome-icon", { attrs: { icon: "arrow-left" } })],
                    1,
                  ),
                  a(
                    "div",
                    {
                      on: {
                        click: function (e) {
                          return t.goto("/extend/tools");
                        },
                      },
                    },
                    [
                      t._v(
                        "\n                Back to the tools list\n            ",
                      ),
                    ],
                  ),
                ]),
                a("div", { staticClass: "loader-zone-title" }, [
                  t._v(t._s(t.title)),
                ]),
                a("img", { attrs: { src: t.img, alt: "main-logo" } }),
                a("p", { staticClass: "description" }, [
                  t._v("\n            " + t._s(t.description) + "\n        "),
                ]),
              ],
            ),
          ]);
        },
        s = [],
        r = a("f8eb"),
        i = {
          name: "ToolPresentation",
          props: {
            removeCover: { type: Boolean, default: !1 },
            description: { type: String, default: "" },
            title: { type: String, default: "" },
            img: { type: String, default: "/Assets/img/banner/logo.svg" },
          },
          mixins: [r["a"]],
          methods: {},
        },
        o = i,
        c = (a("24d8"), a("2877")),
        l = Object(c["a"])(o, n, s, !1, null, "6a125b06", null);
      e["a"] = l.exports;
    },
    d260: function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a(
            "div",
            {
              staticClass: "drag-drop-container",
              on: {
                dragover: function (t) {
                  t.preventDefault();
                },
                drop: function (e) {
                  return (e.preventDefault(), t.handleDrop(e));
                },
              },
            },
            [
              a(
                "div",
                {
                  staticClass: "drag-area",
                  class: { "drag-over": t.isDragging },
                  on: {
                    dragenter: function (e) {
                      t.isDragging = !0;
                    },
                    dragleave: function (e) {
                      t.isDragging = !1;
                    },
                    click: t.handleClick,
                    drop: t.onFileDrop,
                  },
                },
                [
                  t.customContent ? t._t("default") : t._e(),
                  t.file || t.customContent
                    ? t._e()
                    : a("p", [t._v(t._s(t.placeholder))]),
                  t.file && !t.customContent
                    ? a("p", [t._v(t._s(t.file.name))])
                    : t._e(),
                  a(
                    "form",
                    {
                      ref: "formcontainer",
                      on: {
                        submit: function (t) {
                          t.preventDefault();
                        },
                      },
                    },
                    [
                      a("input", {
                        ref: "fileInput",
                        attrs: {
                          type: "file",
                          accept: t.acceptedTypes,
                          hidden: "",
                        },
                        on: { change: t.onFileSelect },
                      }),
                    ],
                  ),
                ],
                2,
              ),
            ],
          );
        },
        s = [],
        r =
          (a("aef6"),
          a("28a5"),
          a("7f7f"),
          {
            name: "FileDragDrop",
            props: {
              acceptedTypes: { type: String, default: ".mcr,.mem,.mcd" },
              placeholder: {
                type: String,
                default: "Suelta tus archivos aqui!",
              },
              customContent: { type: Boolean, default: !1 },
              emitDataview: { type: Boolean, default: !1 },
              disableClick: { type: Boolean, default: !1 },
            },
            data: function () {
              return { file: null, isDragging: !1 };
            },
            methods: {
              softreset: function () {
                this.$refs.fileInput && (this.$refs.fileInput.value = "");
              },
              onFileDrop: function (t) {
                this.isDragging = !1;
                var e = t.dataTransfer.files;
                e.length > 0 && this.processFile(e[0]);
              },
              onFileSelect: function (t) {
                var e = t.target.files;
                e.length > 0 && this.processFile(e[0]);
              },
              processFile: function (t) {
                var e = this;
                this.isFileAccepted(t)
                  ? ((this.file = t),
                    this.$emit("onfileload", t),
                    this.$emit("onfilename", t.name),
                    this.emitDataview &&
                      this.fileToDataView(t).then(function (a) {
                        (e.$emit("ondataviewload", a),
                          e.$emit("onDataviewComplete", {
                            dataview: a,
                            name: t.name,
                          }));
                      }),
                    this.softreset())
                  : this.$emit(
                      "errormessage",
                      "Archivo no soportado, Se aceptan los tipos: ".concat(
                        this.acceptedTypes,
                      ),
                    );
              },
              isFileAccepted: function (t) {
                var e = this.acceptedTypes.split(",").map(function (t) {
                  return t.trim();
                });
                return e.some(function (e) {
                  return t.name.toLowerCase().endsWith(e);
                });
              },
              handleDrop: function (t) {
                this.isDragging = !1;
              },
              handleClick: function () {
                this.disableClick || this.triggerFileInput();
              },
              triggerFileInput: function () {
                this.$refs.fileInput.click();
              },
              fileToDataView: function (t) {
                return new Promise(function (e, a) {
                  var n = new FileReader();
                  ((n.onload = function (t) {
                    var a = t.target.result,
                      n = new DataView(a);
                    e(n);
                  }),
                    (n.onerror = function () {
                      a(new Error("Error al leer el archivo"));
                    }),
                    n.readAsArrayBuffer(t));
                });
              },
            },
          }),
        i = r,
        o = (a("716a"), a("2877")),
        c = Object(o["a"])(i, n, s, !1, null, "b6909aac", null);
      e["a"] = c.exports;
    },
    d31d: function (t, e, a) {
      "use strict";
      var n = a("243e"),
        s = a.n(n);
      s.a;
    },
    d32e: function (t, e, a) {
      "use strict";
      var n = a("31c3"),
        s = a.n(n);
      s.a;
    },
    d3a4: function (t, e, a) {
      "use strict";
      a.d(e, "a", function () {
        return o;
      });
      var n = a("2b0e"),
        s = a("a925"),
        r = a("c3d7"),
        i = a("3673");
      n["a"].use(s["a"]);
      var o = new s["a"]({
        locale: "en",
        fallbackLocale: "en",
        messages: { en: i, es: r },
        silentTranslationWarn: !0,
      });
    },
    d8e9: function (t, e, a) {},
    debf: function (t, e, a) {
      "use strict";
      var n = a("8780"),
        s = a.n(n);
      s.a;
    },
    e50d: function (t, e, a) {
      "use strict";
      var n = a("b85c"),
        s = a.n(n);
      s.a;
    },
    ef35: function (t, e, a) {
      "use strict";
      var n = a("ad69"),
        s = a.n(n);
      s.a;
    },
    f5cf: function (t, e, a) {
      "use strict";
      var n = a("b2e2"),
        s = a.n(n);
      s.a;
    },
    f8eb: function (t, e, a) {
      "use strict";
      (a("a481"), a("386d"), a("3b2b"));
      e["a"] = {
        methods: {
          goto: function (t) {
            location.href = t;
          },
          getCardUrl: function () {
            var t = new RegExp("[\\?&]card=([^&#]*)"),
              e = t.exec(location.search),
              a = null !== e && decodeURIComponent(e[1].replace(/\+/g, " "));
            return parseInt(a);
          },
          getFoeUrl: function () {
            var t = new RegExp("[\\?&]opponent=([^&#]*)"),
              e = t.exec(location.search),
              a = null !== e && decodeURIComponent(e[1].replace(/\+/g, " "));
            return parseInt(a);
          },
          exit: function () {
            (localStorage.removeItem("tks"),
              localStorage.removeItem("user"),
              (document.cookie =
                "ts=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"),
              this.goto("/extend/user/register"));
          },
          check401: function (t) {
            t.response && "401" == t.response.status && this.exit();
          },
        },
      };
    },
    fb12: function (t, e, a) {
      "use strict";
      var n = a("99d5"),
        s = a.n(n);
      s.a;
    },
    fd2d: function (t, e, a) {
      "use strict";
      var n = function () {
          var t = this,
            e = t.$createElement,
            a = t._self._c || e;
          return a("div", { staticClass: "footer" }, [
            a("div", [
              a(
                "div",
                { staticClass: "footertext", staticStyle: { width: "100%" } },
                [
                  a("div", { staticClass: "container" }, [
                    a("div", { staticClass: "content-text" }, [
                      a("div", [
                        a(
                          "div",
                          { staticClass: "left-align teaonline-title" },
                          [
                            a(
                              "svg",
                              {
                                attrs: {
                                  viewBox: "0 0 175.43885 88.493338",
                                  version: "1.1",
                                  xmlns: "http://www.w3.org/2000/svg",
                                  "xmlns:svg": "http://www.w3.org/2000/svg",
                                },
                              },
                              [
                                a("g", [
                                  a("path", {
                                    staticStyle: {
                                      display: "inline",
                                      opacity: "1",
                                      fill: "currentColor",
                                      "fill-opacity": "1",
                                      stroke: "none",
                                      "stroke-width": "0.047625",
                                      "stroke-linecap": "square",
                                      "stroke-opacity": "1",
                                      "paint-order": "markers fill stroke",
                                    },
                                    attrs: {
                                      d: "M 107.58561 16.253891 L 115.56238 46.697511 L 122.31236 39.223032 L 127.03197 63.500102 L 134.5142 60.984494 L 132.34637 69.689389 L 167.88012 46.082044 C 165.53725 55.851405 163.04144 71.895531 160.85161 75.390333 C 158.98026 74.733817 157.23165 74.001928 155.60697 73.193568 C 153.14761 77.369937 149.22053 81.709254 146.08972 85.96023 C 148.3046 85.294554 150.70764 84.440887 153.32597 83.371758 L 153.81948 83.085987 C 153.83751 83.059703 153.85517 83.033193 153.87322 83.006922 C 153.87734 83.020425 153.882 83.034228 153.88614 83.047746 L 195.3048 59.081768 L 172.66381 104.72343 L 167.47343 104.72343 L 168.27958 103.36072 L 162.94192 104.72343 L 160.12814 104.72343 C 160.13103 104.73137 160.13403 104.73926 160.13692 104.7472 L 154.79823 104.74461 L 154.79203 104.72343 L 153.89028 104.72343 L 154.67162 104.29916 L 152.93995 98.203927 L 135.74565 104.72343 L 128.15025 104.72343 C 128.92031 104.02324 129.56397 103.32864 130.10465 102.63828 C 129.31389 102.68807 128.51574 102.72535 127.70945 102.74784 L 127.90116 104.73066 L 113.73821 104.72343 C 114.80364 102.69037 119.37097 100.25976 125.02692 97.376587 C 127.28977 97.735407 129.5951 98.067359 132.32053 97.963632 C 132.88455 95.081483 132.13438 92.255575 131.27512 89.434437 C 130.99619 89.377706 130.77029 89.296062 130.60488 89.186906 C 122.31104 95.12495 115.07653 99.218436 107.58561 103.88937 L 107.58561 100.2467 C 113.81634 96.650533 120.05554 93.222993 127.99522 87.402519 L 127.70945 87.384949 L 128.14508 87.292448 C 134.59548 82.551937 142.16881 76.231053 151.77568 66.952605 L 157.15726 70.054224 L 161.72752 56.006503 C 149.80292 64.264843 136.80929 71.285822 123.75103 78.231503 L 128.15025 68.229529 L 120.6706 71.207642 L 120.6706 66.131983 L 122.40383 62.300692 L 120.30576 48.800741 L 116.83982 51.993311 L 119.11979 54.547161 L 119.11979 74.249834 L 115.47143 77.077568 L 115.7448 55.915553 L 111.36677 52.631515 L 107.58561 36.577715 L 107.58561 16.253891 z M 107.58509 16.253891 L 107.58509 36.577715 L 103.80393 52.631515 L 99.425901 55.915553 L 99.699269 77.077568 L 96.050913 74.249834 L 96.050913 54.547161 L 98.330877 51.993311 L 94.864939 48.800741 L 92.766876 62.300692 L 94.500103 66.131983 L 94.500103 71.207642 L 87.020456 68.229529 L 91.419671 78.231503 C 78.361407 71.285822 65.367781 64.264843 53.443178 56.006503 L 58.013442 70.054224 L 63.395025 66.952605 C 73.001886 76.231053 80.575221 82.551937 87.025624 87.292448 L 87.461256 87.384949 L 87.175486 87.402519 C 95.115165 93.222993 101.35437 96.650533 107.58509 100.2467 L 107.58509 103.88937 C 100.09418 99.218436 92.859667 95.124949 84.565826 89.186906 C 84.400407 89.296062 84.174506 89.377706 83.895583 89.434437 C 83.036323 92.255575 82.286152 95.081483 82.850168 97.963632 C 85.575603 98.067359 87.880931 97.735407 90.14378 97.376587 C 95.799734 100.25976 100.36706 102.69037 101.4325 104.72343 L 87.269537 104.73066 L 87.461256 102.74784 C 86.654964 102.72535 85.856813 102.68807 85.066054 102.63828 C 85.606727 103.32864 86.250387 104.02324 87.020456 104.72343 L 79.425055 104.72343 L 62.230755 98.203927 L 60.499078 104.29916 L 61.280426 104.72343 L 60.378672 104.72343 L 60.372471 104.74461 L 55.033779 104.7472 C 55.036676 104.73926 55.039669 104.73137 55.042564 104.72343 L 52.228782 104.72343 L 46.891123 103.36072 L 47.697276 104.72343 L 42.506895 104.72343 L 19.8659 59.081768 L 61.28456 83.047746 C 61.288699 83.034228 61.293358 83.020425 61.297479 83.006922 C 61.315533 83.033193 61.333191 83.059703 61.351223 83.085987 L 61.844732 83.371758 C 64.463057 84.440887 66.866104 85.294554 69.080983 85.96023 C 65.950174 81.709254 62.023091 77.369937 59.563735 73.193568 C 57.939048 74.001928 56.190438 74.733817 54.319094 75.390333 C 52.129261 71.895531 49.633451 55.851405 47.290582 46.082044 L 82.82433 69.689389 L 80.656504 60.984494 L 88.138734 63.500102 L 92.858343 39.223032 L 99.608319 46.697511 L 107.58509 16.253891 z M 184.85583 71.207642 L 155.49793 87.947189 C 156.02045 89.540324 156.54862 91.252626 157.0167 93.138603 L 157.28232 93.072974 L 179.32283 82.869979 L 184.85583 71.207642 z M 30.314874 71.207642 L 35.84787 82.869979 L 57.888385 93.072974 L 58.154002 93.138603 C 58.622078 91.252626 59.150255 89.540324 59.672772 87.947189 L 30.314874 71.207642 z M 146.37342 76.506544 C 142.37287 80.07744 138.66521 83.126251 135.16739 85.805717 L 141.92408 84.374797 L 146.37342 76.506544 z M 68.79728 76.506544 L 73.24662 84.374797 L 80.003314 85.805717 C 76.505492 83.126251 72.797837 80.07744 68.79728 76.506544 z M 125.14009 81.902597 C 125.36049 81.976063 122.93635 86.931994 122.4493 87.441277 C 121.9851 87.926664 115.7448 90.668986 115.7448 90.668986 C 116.94975 88.5378 118.20186 86.418318 120.12335 84.466264 L 125.14009 81.902597 z M 90.030609 81.902597 L 95.047357 84.466264 C 96.968839 86.418318 98.220947 88.5378 99.425901 90.668986 C 99.425901 90.668986 93.185602 87.926664 92.7214 87.441277 C 92.234347 86.931994 89.810212 81.976063 90.030609 81.902597 z M 149.33396 89.562077 L 138.02923 92.492648 L 136.79623 97.423613 C 138.91077 97.002649 141.28317 96.310585 144.02214 95.229948 C 146.10224 93.534063 147.79831 91.598216 149.33396 89.562077 z M 65.836737 89.562077 C 67.372386 91.598216 69.068464 93.534063 71.148557 95.229948 C 73.887533 96.310585 76.259936 97.002649 78.374473 97.423613 L 77.141473 92.492648 L 65.836737 89.562077 z M 175.21817 89.756897 L 157.73087 96.3875 C 158.22159 98.723772 158.69042 100.44574 159.16282 101.93135 L 171.29593 98.16827 L 175.21817 89.756897 z M 39.952529 89.756897 L 43.87477 98.16827 L 56.007879 101.93135 C 56.480278 100.44574 56.949109 98.723772 57.439833 96.3875 L 39.952529 89.756897 z M 151.57414 93.395435 C 151.22714 93.869096 150.86041 94.319856 150.47653 94.750391 L 151.86198 94.40881 L 151.57414 93.395435 z M 63.596563 93.395435 L 63.308726 94.40881 L 64.694171 94.750391 C 64.31029 94.319856 63.943561 93.869096 63.596563 93.395435 z M 148.60688 102.16751 L 149.37944 104.74151 L 141.28174 104.73738 L 148.60688 102.16751 z M 66.563824 102.16751 L 73.888958 104.73738 L 65.791262 104.74151 L 66.563824 102.16751 z ",
                                      transform:
                                        "matrix(-0.99999999,0,0,0.99999999,195.3048,-16.253891)",
                                    },
                                  }),
                                ]),
                              ],
                            ),
                            t._m(0),
                          ],
                        ),
                      ]),
                      a("div", [
                        a("div", { staticClass: "izquierda" }, [
                          t._v(
                            "\n                            " +
                              t._s(t.$t("mensajeContacto")) +
                              "\n                        ",
                          ),
                        ]),
                        a("div", { staticClass: "contact" }, [
                          a(
                            "a",
                            {
                              staticClass: "izquierda",
                              attrs: { href: "mailto:admin@teaonline.xyz" },
                            },
                            [
                              a("font-awesome-icon", {
                                attrs: { icon: ["far", "envelope"] },
                              }),
                              t._v(
                                " admin@teaonline.xyz\n                            ",
                              ),
                            ],
                            1,
                          ),
                          a(
                            "a",
                            {
                              staticClass: "izquierda",
                              attrs: {
                                href: "http://www.facebook.com/Tea.Administrador",
                              },
                            },
                            [
                              a("font-awesome-icon", {
                                attrs: { icon: ["fab", "facebook-square"] },
                              }),
                              t._v(
                                "\n                                Tea.Administrador\n                            ",
                              ),
                            ],
                            1,
                          ),
                        ]),
                        a(
                          "div",
                          {
                            staticClass: "izquierda",
                            staticStyle: { "margin-top": "1em" },
                          },
                          [
                            t._v(
                              "\n                            " +
                                t._s(t.$t("SupportKeepGoing")) +
                                "\n                        ",
                            ),
                          ],
                        ),
                        a("div", { staticClass: "contact" }, [
                          a(
                            "a",
                            {
                              staticClass: "izquierda",
                              attrs: { href: "https://paypal.me/teaonline" },
                            },
                            [
                              a("font-awesome-icon", {
                                attrs: { icon: ["fab", "paypal"] },
                              }),
                              t._v(" Paypal\n                            "),
                            ],
                            1,
                          ),
                        ]),
                      ]),
                      a("div"),
                    ]),
                  ]),
                ],
              ),
            ]),
            t._m(1),
          ]);
        },
        s = [
          function () {
            var t = this,
              e = t.$createElement,
              a = t._self._c || e;
            return a("div", [
              a("span", { staticClass: "tea" }, [t._v("TEA")]),
              a("span", { staticClass: "online" }, [t._v("ONLINE")]),
            ]);
          },
          function () {
            var t = this,
              e = t.$createElement,
              a = t._self._c || e;
            return a("div", { staticClass: "footer-bot" }, [
              a("div", [
                a("span", [t._v("@MMProjects")]),
                a("span", [t._v("\n                v1.3.0.0\n            ")]),
              ]),
            ]);
          },
        ],
        r = (a("8e6e"), a("ac6a"), a("456d"), a("bd86")),
        i = a("2b0e"),
        o = a("ecee"),
        c = a("f2d1"),
        l = a("ad3d"),
        u = a("2f62");
      function d(t, e) {
        var a = Object.keys(t);
        if (Object.getOwnPropertySymbols) {
          var n = Object.getOwnPropertySymbols(t);
          (e &&
            (n = n.filter(function (e) {
              return Object.getOwnPropertyDescriptor(t, e).enumerable;
            })),
            a.push.apply(a, n));
        }
        return a;
      }
      function h(t) {
        for (var e = 1; e < arguments.length; e++) {
          var a = null != arguments[e] ? arguments[e] : {};
          e % 2
            ? d(a, !0).forEach(function (e) {
                Object(r["a"])(t, e, a[e]);
              })
            : Object.getOwnPropertyDescriptors
              ? Object.defineProperties(t, Object.getOwnPropertyDescriptors(a))
              : d(a).forEach(function (e) {
                  Object.defineProperty(
                    t,
                    e,
                    Object.getOwnPropertyDescriptor(a, e),
                  );
                });
        }
        return t;
      }
      (o["c"].add(c["c"], c["b"]),
        i["a"].component("font-awesome-icon", l["a"]));
      var p = {
          name: "footerp",
          computed: h({}, Object(u["c"])(["base"])),
          mounted: function () {},
        },
        f = p,
        m = (a("d31d"), a("2877")),
        g = Object(m["a"])(f, n, s, !1, null, "2500199f", null);
      e["a"] = g.exports;
    },
  },
]);
