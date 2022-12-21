var API_GET_ALLOWLIST = "/allowlist";
var API_SERVICES = "/settings/service";
var API_CRUD_ALLOWLIST = "/allowlist/entry/";
var API_EXECLOG = "/execution/";
var API_KEY = "";

// Utility functions
function convertJsonToGet(formJSON) {
  let formURL = "";
  for (var key in formJSON) {
    formURL += key + "=" + formJSON[key] + "&";
  }
  formURL.substr(0, formURL.length - 1);
  return formURL;
}

// Init Vue instance
var app = new Vue({
  el: "#app",
  data: {
    accountId: "",
    apiKey: "",
    allowlistExpanded: false,
    executionLogExpanded: false,
    executionLogActionStats: {},
    executionLogDataTables: "",
    executionLogKey: "",
    executionLogList: [],
    executionLogMode: "",
    executionLogRegionStats: {},
    executionLogSearchTerm: "",
    executionLogServiceStats: {},
    executionLogTable: [],
    resourceIdPlaceholder: "",
    resourceList: [],
    selectedComment: "",
    selectedExpiration: 0,
    selectedOwner: "",
    selectedResource: "",
    selectedResourceId: "",
    selectedService: "",
    serviceList: [],
    serviceSettings: [],
    serviceSettingsFlat: [],
    showApiKeyPopup: true,
    showExecutionLogListLoadingGif: false,
    showExecutionLogLoadingGif: false,
    showExecutionLogPopup: false,
    showHelpPopup: false,
    showAllowlistDeletePopup: false,
    showAllowlistLoadingGif: false,
    showAllowlistPopup: false,
    allowlist: [],
    allowlistDataTables: "",
    allowlistSearchTerm: "",
  },
  methods: {
    // Allowlist
    closeAllowlistDeletePopup: function () {
      this.selectedResourceId = "";
      this.showAllowlistDeletePopup = false;
    },
    closeAllowlistInsertPopup: function () {
      this.resourceIdPlaceholder = "";
      this.resourceList = [];
      this.selectedComment = "";
      this.selectedExpiration = 0;
      this.selectedOwner = "";
      this.selectedResource = "";
      this.selectedResourceId = "";
      this.selectedService = "";
      this.showAllowlistPopup = false;
    },
    createAllowlistEntry: function () {
      let formData = {
        resource_id:
          this.selectedService +
          ":" +
          this.selectedResource +
          ":" +
          this.selectedResourceId,
        owner: this.selectedOwner,
        comment: this.selectedComment,
      };

      sendApiRequest(convertJsonToGet(formData), "POST");
    },
    createAllowlistEntryFromExecutionLog: function (
      service,
      resource,
      resourceId
    ) {
      this.selectedService = service.toLowerCase().replace(/ /g, "_");
      this.selectedResource = resource.toLowerCase().replace(/ /g, "_");
      this.selectedResourceId = resourceId;
      this.updateResourceList(this.selectedService);
      this.closeExecutionLogPopup();
      this.openAllowlistInsertPopup();
    },
    deleteAllowlistEntry: function (resourceId) {
      let formData = {
        resource_id: resourceId,
      };

      sendApiRequest(convertJsonToGet(formData), "DELETE");
    },
    expandAllowlist: function () {
      if (this.allowlistExpanded) {
        $("#allowlist-message-body").css({ "max-height": "calc(36vh)" });
        $("#allowlist-message-body").css({ "min-height": "" });
        $("#allowlist-expand-icon").attr(
          "class",
          "fas fa-up-right-and-down-left-from-center"
        );
        // $("html").removeClass("remove-overflow");
        this.allowlistExpanded = false;
      } else {
        $("#allowlist-message-body").css({ "max-height": "calc(90vh)" });
        $("#allowlist-message-body").css({ "min-height": "calc(90vh)" });
        $("#allowlist-expand-icon").attr(
          "class",
          "fas fa-down-left-and-up-right-to-center"
        );
        // $("html").addClass("remove-overflow");
        $("html, body").animate(
          { scrollTop: $("#allowlist-message").offset().top - 20 },
          500
        );
        this.allowlistExpanded = true;
      }
    },
    expandExecutionLog: function () {
      if (this.executionLogExpanded) {
        $("#execution-log-message-body").css({ "max-height": "calc(36vh)" });
        $("#execution-log-message-body").css({ "min-height": "" });
        $("#execution-log-expand-icon").attr(
          "class",
          "fas fa-up-right-and-down-left-from-center"
        );
        // $("html").removeClass("remove-overflow");
        this.executionLogExpanded = false;
      } else {
        $("#execution-log-message-body").css({ "max-height": "calc(90vh)" });
        $("#execution-log-message-body").css({ "min-height": "calc(90vh)" });
        $("#execution-log-expand-icon").attr(
          "class",
          "fas fa-down-left-and-up-right-to-center"
        );
        // $("html, body").animate({ scrollTop: $(document).height() }, 1000);
        $("html, body").animate(
          { scrollTop: $("#execution-log-message").offset().top - 20 },
          500
        );

        // $("html").addClass("remove-overflow");
        this.executionLogExpanded = true;
      }
    },
    extendAllowlistEntry: function (rowId) {
      let row = this.allowlist[rowId - 1];
      let formData = {
        resource_id: row.resource_id,
        expiration: row.expiration,
        owner: row.owner,
        comment: row.comment,
      };

      sendApiRequest(convertJsonToGet(formData), "PUT");
    },
    updateResourceId: function (service, resource) {
      this.resourceIdPlaceholder =
        this.serviceSettings[service][resource]["id"];
    },
    updateResourceList: function (service) {
      this.resourceList = Object.keys(this.serviceSettings[service]);

      // auto select if only 1 option exists
      if (this.resourceList.length === 1) {
        this.selectedResource = this.resourceList[0];
        this.updateResourceId(service, this.resourceList[0]);
      } else {
        this.resourceIdPlaceholder = "";
      }
    },
    openAllowlistDeletePopup: function (resourceId) {
      this.selectedResourceId = resourceId;
      this.showAllowlistDeletePopup = true;
      this.resourceIdPlaceholder = "";
    },
    openAllowlistInsertPopup: function () {
      this.showAllowlistPopup = true;
      this.resourceIdPlaceholder = "";
    },
    searchAllowlist: function () {
      this.allowlistDataTables.search(this.allowlistSearchTerm).draw();
    },
    showTemporaryAllowlist: function () {
      this.allowlistDataTables.column(6).search("Temporary").draw();
      $("#show-temporary-allowlist-button").addClass("is-link");
      $("#show-permanent-allowlist-button").removeClass("is-link");
    },
    showPermanentAllowlist: function () {
      this.allowlistDataTables.column(6).search("Permanent").draw();
      $("#show-permanent-allowlist-button").addClass("is-link");
      $("#show-temporary-allowlist-button").removeClass("is-link");
    },
    // Execution Log
    closeExecutionLogPopup: function () {
      $("html").removeClass("remove-overflow");
      this.executionLogDataTables.clear().draw();

      // Reseet variables
      this.executionLogActionStats = {};
      this.executionLogKey = "";
      this.executionLogMode = "";
      this.executionLogRegionStats = {};
      this.executionLogServiceStats = {};
      this.executionLogTable = [];

      this.showExecutionLogPopup = false;
    },
    openExecutionLog: function (keyURL) {
      $("html").addClass("remove-overflow");

      getExecutionLog(keyURL);
    },
    searchExecutionLog: function () {
      this.executionLogDataTables.search(this.executionLogSearchTerm).draw();
    },
    // Help
    closeHelpPopup: function () {
      this.showHelpPopup = false;
    },
    openHelpPopup: function () {
      this.showHelpPopup = true;
    },
    // Api Key
    closeApiKeyPopup: function () {
      this.showApiKeyPopup = false;
    },
    setApiKey: function () {
      this.showApiKeyPopup = false;
      API_KEY = this.apiKey;
      localStorage.setItem("x-api-key", this.apiKey);
      init();
    },
    resetApiKey: function () {
      API_KEY = "";
      localStorage.removeItem("x-api-key");
      location.reload();
    },
  },
  mounted: function () {
    API_KEY = localStorage.getItem("x-api-key");
    if (API_KEY !== null) {
      this.showApiKeyPopup = false;
    }
  },
});

function sendApiRequest(formURL, requestMethod) {
  fetch(API_CRUD_ALLOWLIST + "?" + formURL, {
    method: requestMethod,
    headers: {
      "x-api-key": API_KEY,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      refreshAllowlist();
      app.closeAllowlistInsertPopup();
      app.closeAllowlistDeletePopup();

      iziToast.success({
        color: "#3FBF61",
        message: data.message,
        messageColor: "white",
      });
    })
    .catch((error) => {
      iziToast.error({
        color: "#EC2B55",
        message: error,
        messageColor: "white",
        title: "Something went wrong",
      });
    });
}

// Get execution log for a single instance
function getExecutionLog(executionLogUrl) {
  app.showExecutionLogPopup = true;
  app.showExecutionLogLoadingGif = true;

  fetch(API_EXECLOG + executionLogUrl, {
    headers: {
      "x-api-key": API_KEY,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      app.executionLogKey = decodeURIComponent(executionLogUrl);
      app.executionLogTable = data["response"]["body"];

      if (data["response"]["is_compressed"]) {
        try {
          let compressedData = Uint8Array.from(
            atob(app.executionLogTable),
            (c) => c.charCodeAt(0)
          );
          let decompressedData = pako.inflate(compressedData, { to: "string" });
          app.executionLogTable = JSON.parse(decompressedData);
        } catch (error) {
          console.log(error);
        }
      }

      app.executionLogActionStats = data["response"]["statistics"]["action"];
      app.executionLogServiceStats = data["response"]["statistics"]["service"];
      app.executionLogRegionStats = data["response"]["statistics"]["region"];
      app.executionLogMode =
        data["response"]["is_dry_run"] === true ? "Dry Run" : "Destroy";

      setTimeout(function () {
        if (!app.executionLogDataTables) {
          app.executionLogDataTables = $("#execution-log-table").DataTable({
            data: app.executionLogTable,
            autoWidth: true,
            deferRender: true,
            pageLength: 500,
            dom: "rtip",
            columnDefs: [
              {
                targets: 5,
                className: "dt-body-nowrap",
              },
            ],
          });
        } else {
          app.executionLogDataTables
            .clear()
            .rows.add(app.executionLogTable)
            .draw();
        }
        app.showExecutionLogLoadingGif = false;
        $("#execution-log-table-info").html($("#execution-log-table_info"));
        $("#execution-log-table-paginate").html(
          $("#execution-log-table_paginate")
        );
      }, 10);
    })
    .catch((error) => {
      iziToast.error({
        color: "#EC2B55",
        message: error,
        messageColor: "white",
        title: "Something went wrong",
      });
    });
}

// Get execution logs list
function getExecutionLogList() {
  app.showExecutionLogListLoadingGif = true;
  fetch(API_EXECLOG, {
    headers: {
      "x-api-key": API_KEY,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      app.executionLogList = data["response"]["logs"].map((row) => {
        let logDate = new Date(row["date"] + " UTC");
        let localDate = logDate.toString().split(/ GMT/)[0];

        row["key_escape"] = encodeURIComponent(row["key"]);
        row["local_date"] = localDate;
        return row;
      });
      setTimeout(function () {
        $("#execution-log-list-table").DataTable({
          dom: "rtp",
          columnDefs: [
            { orderable: false, targets: [0, 1, 2] },
            { className: "dt-center", targets: [2] },
          ],
          pageLength: 500,
          order: [[0, "desc"]],
        });
        $("#execution-log-list-table-paginate").html(
          $("#execution-log-list-table_paginate")
        );
      }, 10);
      app.showExecutionLogListLoadingGif = false;
    })
    .catch((error) => {
      iziToast.error({
        color: "#EC2B55",
        message: error,
        messageColor: "white",
        title: "Something went wrong",
      });
    });
}

// Get supported services
function getServices() {
  fetch(API_SERVICES, {
    headers: {
      "x-api-key": API_KEY,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      app.serviceSettings = data["response"];

      // get list of supported services
      app.serviceList = Object.keys(data["response"]);

      // convert settings to flat table
      for (const service in data["response"]) {
        for (resource in data["response"][service]) {
          app.serviceSettingsFlat.push({
            service: service,
            resource: resource,
            ttl: data["response"][service][resource]["ttl"],
            enabled: data["response"][service][resource]["clean"],
          });
        }
      }
    })
    .catch((error) => {
      iziToast.error({
        color: "#EC2B55",
        message: error,
        messageColor: "white",
        title: "Something went wrong",
        titleColor: "white",
      });
    });
}

// Get allowlist
function getAllowlist() {
  app.allowlist = [];
  app.showAllowlistLoadingGif = true;
  fetch(API_GET_ALLOWLIST, {
    headers: {
      "x-api-key": API_KEY,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      let i = 1;
      let allowlistRaw = data["response"]["allowlist"];

      dayjs.extend(dayjs_plugin_utc);
      dayjs.extend(dayjs_plugin_timezone);

      app.allowlist = allowlistRaw.map((item) => {
        // Parse Resource ID, i.e. split on ":"
        let parsedResourceId = item["resource_id"].split(":", 2);
        parsedResourceId.push(
          item["resource_id"].slice(parsedResourceId.join("").length + 2)
        );

        let readableDate = dayjs.unix(item["expiration"]).tz(dayjs.tz.guess());

        item["row_id"] = i++;
        item["service"] = parsedResourceId[0];
        item["resource"] = parsedResourceId[1];
        item["id"] = parsedResourceId[2];

        item["expiration_readable"] = readableDate.format("DD MMM YYYY");

        item["expiration_tooltip"] = readableDate.format(
          "ddd MMM DD HH:mm:ss YYYY"
        );

        return item;
      });

      setTimeout(function () {
        app.allowlistDataTables = $("#allowlist").DataTable({
          dom: "rtp",
          columnDefs: [
            { className: "dt-center", targets: [5] },
            { orderable: false, targets: [0, 1, 2, 3, 4, 5, 6, 7] },
            {
              targets: [6],
              visible: false,
            },
            { responsivePriority: 1, targets: 7 },
          ],
          order: [[6, "desc"]],
          pageLength: 500,
        });
        $("#allowlist-paginate").html($("#allowlist_paginate"));
        app.allowlistDataTables.column(6).search("Temporary").draw();
        app.showAllowlistLoadingGif = false;
      }, 10);
    })
    .catch((error) => {
      iziToast.error({
        color: "#EC2B55",
        message: error,
        messageColor: "white",
        title: "Something went wrong",
      });
    });
}

function refreshAllowlist() {
  app.allowlistDataTables.destroy();
  getAllowlist();
}

function openTab(evt, tabName) {
  var i, x, tablinks;

  x = document.getElementsByClassName("content-tab");
  for (i = 0; i < x.length; i++) {
    x[i].style.display = "none";
  }

  tablinks = document.getElementsByClassName("tab");
  for (i = 0; i < x.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" is-active", "");
  }

  document.getElementById(tabName).style.display = "block";
  evt.currentTarget.className += " is-active";
}

function init() {
  getAllowlist();
  getExecutionLogList();
  getServices();
}

// Get the API Gateway Base URL from manifest file
fetch("serverless.manifest.json").then(function (response) {
  response.json().then(function (data) {
    let env = Object.keys(data)[0];
    let API_BASE = data[env]["urls"]["apiGatewayBaseURL"];

    API_GET_ALLOWLIST = API_BASE + API_GET_ALLOWLIST;
    API_SERVICES = API_BASE + API_SERVICES;
    API_CRUD_ALLOWLIST = API_BASE + API_CRUD_ALLOWLIST;
    API_EXECLOG = API_BASE + API_EXECLOG;

    for (output of data[env]["outputs"]) {
      if (output["OutputKey"] === "AccountID") {
        app.accountId = output["OutputValue"];
        document.title = "AWS Auto Cleanup - " + output["OutputValue"];
        break;
      }
    }
    if (API_KEY) {
      init();
    }
  });
});
