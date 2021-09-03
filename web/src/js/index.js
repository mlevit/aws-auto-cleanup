var API_GET_WHITELIST = "/whitelist";
var API_SERVICES = "/settings/service";
var API_CRUD_WHITELIST = "/whitelist/entry/";
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
    showWhitelistDeletePopup: false,
    showWhitelistLoadingGif: false,
    showWhitelistPopup: false,
    whitelist: [],
    whitelistDataTables: "",
    whitelistSearchTerm: "",
  },
  methods: {
    // Whitelist
    closeWhitelistDeletePopup: function () {
      this.selectedResourceId = "";
      this.showWhitelistDeletePopup = false;
    },
    closeWhitelistInsertPopup: function () {
      this.resourceIdPlaceholder = "";
      this.resourceList = [];
      this.selectedComment = "";
      this.selectedExpiration = 0;
      this.selectedOwner = "";
      this.selectedResource = "";
      this.selectedResourceId = "";
      this.selectedService = "";
      this.showWhitelistPopup = false;
    },
    createWhitelistEntry: function () {
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
    createWhitelistEntryFromExecutionLog: function (
      service,
      resource,
      resourceId
    ) {
      this.selectedService = service.toLowerCase().replace(/ /g, "_");
      this.selectedResource = resource.toLowerCase().replace(/ /g, "_");
      this.selectedResourceId = resourceId;
      this.updateResourceList(this.selectedService);
      this.closeExecutionLogPopup();
      this.openWhitelistInsertPopup();
    },
    deleteWhitelistEntry: function (resourceId) {
      let formData = {
        resource_id: resourceId,
      };

      sendApiRequest(convertJsonToGet(formData), "DELETE");
    },
    extendWhitelistEntry: function (rowId) {
      let row = this.whitelist[rowId - 1];
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
    openWhitelistDeletePopup: function (resourceId) {
      this.selectedResourceId = resourceId;
      this.showWhitelistDeletePopup = true;
      this.resourceIdPlaceholder = "";
    },
    openWhitelistInsertPopup: function () {
      this.showWhitelistPopup = true;
      this.resourceIdPlaceholder = "";
    },
    searchWhitelist: function () {
      this.whitelistDataTables.search(this.whitelistSearchTerm).draw();
    },
    // Execution Log
    closeExecutionLogPopup: function () {
      this.executionLogDataTables.destroy();

      this.executionLogActionStats = {};
      this.executionLogRegionStats = {};
      this.executionLogServiceStats = {};
      this.showExecutionLogPopup = false;
    },
    openExecutionLog: function (keyURL) {
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
  fetch(API_CRUD_WHITELIST + "?" + formURL, {
    method: requestMethod,
    headers: {
      "x-api-key": API_KEY,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      refreshWhitelist();
      app.closeWhitelistInsertPopup();
      app.closeWhitelistDeletePopup();

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
      app.executionLogTable = data["response"]["body"];
      app.executionLogKey = decodeURIComponent(executionLogUrl);

      setTimeout(function () {
        app.executionLogDataTables = $("#execution-log-table").DataTable({
          autoWidth: true,
          columnDefs: [
            { orderable: false, targets: [6] },
            { className: "dt-center", targets: [6] },
          ],
          dom: "lrti",
          paging: false,
        });
        app.showExecutionLogLoadingGif = false;
      }, 10);

      // Get execution mode

      if (data["response"]["body"][0][7] == "True") {
        app.executionLogMode = "Dry Run";
      } else {
        app.executionLogMode = "Destroy";
      }

      for (const log of data["response"]["body"]) {
        // action taken
        app.executionLogActionStats[log["5"]] =
          ++app.executionLogActionStats[log["5"]] || 1;

        // service and resource
        app.executionLogServiceStats[log["2"] + " " + log["3"]] =
          ++app.executionLogServiceStats[log["2"] + " " + log["3"]] || 1;

        // region
        app.executionLogRegionStats[log["1"]] =
          ++app.executionLogRegionStats[log["1"]] || 1;
      }
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
        let log_date = new Date(row["date"] + " UTC");
        let local_date = log_date.toString().split(/ GMT/)[0];

        row["key_escape"] = encodeURIComponent(row["key"]);
        row["local_date"] = local_date;
        return row;
      });
      setTimeout(function () {
        $("#execution-log-list-table").DataTable({
          dom: "rtp",
          columnDefs: [
            { orderable: false, targets: [0, 1, 2] },
            { className: "dt-center", targets: [2] },
          ],
          order: [[0, "desc"]],
        });
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

// Get whitelist
function getWhitelist() {
  app.whitelist = [];
  app.showWhitelistLoadingGif = true;
  fetch(API_GET_WHITELIST, {
    headers: {
      "x-api-key": API_KEY,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      let i = 1;
      let whitelistRaw = data["response"]["whitelist"];

      dayjs.extend(dayjs_plugin_utc);
      dayjs.extend(dayjs_plugin_timezone);

      app.whitelist = whitelistRaw.map((item) => {
        let readableDate = dayjs.unix(item["expiration"]).tz(dayjs.tz.guess());

        item["row_id"] = i++;
        item["service"] = item["resource_id"].split(":", 3)[0];
        item["resource"] = item["resource_id"].split(":", 3)[1];
        item["id"] = item["resource_id"].split(":", 3)[2];

        item["expiration_readable"] = readableDate.format(
          "ddd MMM DD HH:mm:ss YYYY"
        );

        return item;
      });

      setTimeout(function () {
        app.whitelistDataTables = $("#whitelist").DataTable({
          columnDefs: [
            { className: "dt-center", targets: [5] },
            { orderable: false, targets: [0, 1, 2, 3, 4, 5, 6, 7] },
            {
              targets: [6],
              visible: false,
              searchable: false,
            },
          ],
          dom: "rtp",
          order: [[6, "desc"]],
          pageLength: 20,
          rowGroup: {
            dataSrc: 6,
          },
        });
      }, 10);

      app.showWhitelistLoadingGif = false;
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

function refreshWhitelist() {
  app.whitelistDataTables.destroy();
  getWhitelist();
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
  getWhitelist();
  getExecutionLogList();
  getServices();
}

// Get the API Gateway Base URL from manifest file
fetch("serverless.manifest.json").then(function (response) {
  response.json().then(function (data) {
    let API_BASE = data["prod"]["urls"]["apiGatewayBaseURL"];

    API_GET_WHITELIST = API_BASE + API_GET_WHITELIST;
    API_SERVICES = API_BASE + API_SERVICES;
    API_CRUD_WHITELIST = API_BASE + API_CRUD_WHITELIST;
    API_EXECLOG = API_BASE + API_EXECLOG;

    for (output of data["prod"]["outputs"]) {
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
