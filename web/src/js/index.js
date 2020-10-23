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
    executionLogKey: "",
    executionLogList: [],
    executionLogMode: false,
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
    settings: [],
    settingsFlat: [],
    showExecutionLogListLoadingGif: false,
    showExecutionLogLoadingGif: false,
    showExecutionLogPopup: false,
    showHelpPopup: false,
    showWhitelistDeletePopup: false,
    showWhitelistLoadingGif: false,
    showWhitelistPopup: false,
    whitelist: [],
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
      this.resourceIdPlaceholder = this.settings[service][resource]["id"];
    },
    updateResourceList: function (service) {
      this.resourceList = Object.keys(this.settings[service]);
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
    // Execution Log
    openExecutionLog: function (keyURL) {
      getExecutionLog(keyURL);
    },
    closeExecutionLogPopup: function () {
      $("#execution-log-table").DataTable().destroy();
      this.showExecutionLogPopup = false;
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

      if (data["response"]["body"][0][7] == "True") {
        app.executionLogMode = "Dry Run";
      } else {
        app.executionLogMode = "Destroy";
      }

      setTimeout(function () {
        $("#execution-log-table").DataTable({
          autoWidth: true,
          columnDefs: [
            {
              className: "dt-body-nowrap",
              targets: [1, 2, 3, 5],
            },
            { className: "dt-nowrap", targets: [1, 2, 3, 5] },
          ],
          paging: false,
        });
        app.showExecutionLogLoadingGif = false;
      }, 10);
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
          columnDefs: [
            { orderable: false, targets: [2] },
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

// Get settings
function getSettings() {
  fetch(API_SERVICES)
    .then((response) => response.json())
    .then((data) => {
      app.settings = data["response"];
      app.serviceList = Object.keys(data["response"]);

      // console.log(data["response"]);

      for (service in data["response"]) {
        for (resource in data["response"][service]) {
          app.settingsFlat.push({
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
      let whitelist_raw = data["response"]["whitelist"];
      // Add row ID for action reference
      app.whitelist = whitelist_raw.map((item) => {
        item["id"] = i++;
        dayjs.extend(dayjs_plugin_utc);
        dayjs.extend(dayjs_plugin_timezone);

        let readable_date = dayjs.unix(item["expiration"]).tz(dayjs.tz.guess());

        item["expiration_readable"] = readable_date.format(
          "ddd MMM DD HH:mm:ss YYYY"
        );

        return item;
      });

      setTimeout(function () {
        $("#whitelist").DataTable({
          columnDefs: [
            { orderable: false, targets: [3, 4] },
            { className: "dt-center", targets: [4] },
            {
              className: "dt-body-nowrap",
              targets: [0, 1, 2],
            },
          ],
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
  fetch(API_GET_WHITELIST)
    .then((response) => response.json())
    .then((data) => {
      let i = 1;
      let whitelist_raw = data["response"]["whitelist"];
      app.whitelist = whitelist_raw.map((item) => {
        item["id"] = i++;
        dayjs.extend(dayjs_plugin_utc);
        dayjs.extend(dayjs_plugin_timezone);

        let readable_date = dayjs.unix(item["expiration"]).tz(dayjs.tz.guess());

        item["expiration_readable"] = readable_date.format(
          "ddd MMM DD HH:mm:ss YYYY"
        );
        return item;
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

// Get the API Gateway Base URL from manifest file
fetch("serverless.manifest.json").then(function (response) {
  response.json().then(function (data) {
    let API_BASE = data["prod"]["urls"]["apiGatewayBaseURL"];

    API_GET_WHITELIST = API_BASE + API_GET_WHITELIST;
    API_SERVICES = API_BASE + API_SERVICES;
    API_CRUD_WHITELIST = API_BASE + API_CRUD_WHITELIST;
    API_EXECLOG = API_BASE + API_EXECLOG;

    getWhitelist();
    getExecutionLogList();
    getSettings();
  });
});
