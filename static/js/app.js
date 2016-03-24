var WS_URL = "ws://" + location.host + "/receive";
var alert = document.getElementById("tracker-msg");

// plot charts
function plotCharts(scores) {
    var ctx = document.getElementById("trend").getContext("2d");
    var ranks = [];
    var histogram = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    for (var i = 1; i <= scores.length; i++) {
      ranks.push(i);
      var index = parseInt(scores[i-1] / 10);
      histogram[index] += 1;
      scores[i-1] = scores[i-1].toFixed(2);
    }
    var data = {
        labels: ranks,
        datasets: [
            {
                label: "My first dataset",
                fillColor: "rgba(220,220,220,0.2)",
                strokeColor: "rgba(220,220,220,1)",
                pointColor: "rgba(220,220,220,1)",
                pointStrokeColor: "#fff",
                pointHighlightFill: "#fff",
                pointHighlightStroke: "rgba(220,220,220,1)",
                data: scores
            }
        ]
    };
    var myNewChart = new Chart(ctx).Line(data, {
        "showTooltips": false
    });

    var histodata = {
        labels: ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60", "60-70", "70-80", "80-90", "90-100"],
        datasets: [
            {
                label: "My first dataset",
                fillColor: "rgba(220,220,220,0.2)",
                strokeColor: "rgba(220,220,220,1)",
                pointColor: "rgba(220,220,220,1)",
                pointStrokeColor: "#fff",
                pointHighlightFill: "#fff",
                pointHighlightStroke: "rgba(220,220,220,1)",
                data: histogram
            }
        ]
    }
    var ctx2 = document.getElementById("histo").getContext("2d");
    var myhistochart = new Chart(ctx2).Bar(histodata);
}

var app = new Vue({
    el: "#app",

    data: {
        rank: 0,
        email: null,
        leaders: []
    },

    created: function() {
        this.startTracking();
        this.fetchData();
    },

    methods: {
        showMsg: function() {
            alert.style.display = "block";
            setTimeout(function() {
                alert.style.display = "none";
            }, 3*1000);
        },
        fetchData: function() {
            console.info("fetching data");
            var xhr = new XMLHttpRequest();
            var self = this;
            xhr.open("GET", "/leaderboard.json");
            xhr.onload = function() {
                var resp = JSON.parse(xhr.responseText);
                self.rank = resp.rank;
                self.email = resp.email;
                self.leaders = resp.leaders;
                plotCharts(resp.scores);
            }
            xhr.send();
        },
        
        startTracking: function() {
            var self = this;

            this.inbox = new ReconnectingWebSocket(WS_URL);

            this.inbox.onclose = function() {
                console.log("inbox closed");
                this.inbox = new WebSocket(this.inbox.url);
            };

            this.inbox.onmessage = function(message) {
                var msg = JSON.parse(message.data);
                if (msg.type === "INFO") {
                    console.info("connected");
                }
                if (msg.type === "UPDATE") {
                    console.log("updating the table");
                    self.fetchData();
                    self.showMsg();
                }
            };
        }
    }

});
