var API_GET_WHITELIST = "/whitelist";
var API_SERVICES = "/settings/service";
var API_CRUD_WHITELIST = "/whitelist/entry/";
var API_EXECLOG = "/execution/";

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
    deleteWhitelistEntry: function (resourceID) {
      let formData = {
        resource_id: resourceID,
      };

      sendApiRequest(convertJsonToGet(formData), "DELETE");
    },
    extendWhitelistEntry: function (rowID) {
      let row = this.whitelist[rowID - 1];
      let formData = {
        resource_id: row.resource_id,
        expiration: row.expiration,
        owner: row.owner,
        comment: row.comment,
      };

      sendApiRequest(convertJsonToGet(formData), "PUT");
    },
    updateResourceID: function (service, resource) {
      this.resourceIdPlaceholder = this.serviceSettings[service][resource][
        "id"
      ];
    },
    updateResourceList: function (service) {
      this.resourceList = Object.keys(this.serviceSettings[service]);
      this.resourceIdPlaceholder = "";
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
  },
});

function sendApiRequest(formURL, requestMethod) {
  fetch(API_CRUD_WHITELIST + "?" + formURL, {
    method: requestMethod,
  })
    .then((response) => response.json())
    .then((data) => {
      refreshWhitelist();
      app.closeWhitelistInsertPopup();
      app.closeWhitelistDeletePopup();

      iziToast.success({
        message: data.message,
        color: "#3FBF61",
        messageColor: "white",
      });
    })
    .catch((error) => {
      iziToast.error({
        title: "Something went wrong",
        message: error,
        color: "#EC2B55",
        messageColor: "white",
      });
    });
}

// Get execution log for a single instance
function getExecutionLog(executionLogURL) {
  app.showExecutionLogPopup = true;
  app.showExecutionLogLoadingGif = true;

  fetch(API_EXECLOG + executionLogURL)
    .then((response) => response.json())
    .then((data) => {
      app.executionLogTable = data["response"]["body"];
      app.executionLogKey = decodeURIComponent(executionLogURL);

      setTimeout(function () {
        app.executionLogDataTables = $("#execution-log-table").DataTable({
          dom: "lrti",
          autoWidth: true,
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
        title: "Something went wrong",
        message: error,
        color: "#EC2B55",
        messageColor: "white",
      });
    });
}

// Get execution logs list
function getExecutionLogList() {
  app.showExecutionLogListLoadingGif = true;
  fetch(API_EXECLOG)
    .then((response) => response.json())
    .then((data) => {
      app.executionLogList = data["response"]["logs"].map((row) => {
        row["key_escape"] = encodeURIComponent(row["key"]);
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
        title: "Something went wrong",
        message: error,
        color: "#EC2B55",
        messageColor: "white",
      });
    });
}

// Get supported services
function getServices() {
  fetch(API_SERVICES)
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
        title: "Something went wrong",
        message: error,
        color: "#EC2B55",
        titleColor: "white",
        messageColor: "white",
      });
    });
}

// Get whitelist
function getWhitelist() {
  app.whitelist = [];
  app.showWhitelistLoadingGif = true;
  fetch(API_GET_WHITELIST)
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
        title: "Something went wrong",
        message: error,
        color: "#EC2B55",
        messageColor: "white",
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

    getWhitelist();
    getExecutionLogList();
    getServices();
  });
});
