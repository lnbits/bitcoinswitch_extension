window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      protocol: window.location.protocol,
      location: window.location.hostname,
      wslocation: window.location.hostname,
      filter: '',
      currency: 'USD',
      lnurlValue: '',
      websocketMessage: '',
      bitcoinswitches: [],
      bitcoinswitchTable: {
        columns: [
          {
            name: 'title',
            align: 'left',
            label: 'title',
            field: 'title'
          },
          {
            name: 'wallet',
            align: 'left',
            label: 'wallet',
            field: 'wallet'
          },
          {
            name: 'currency',
            align: 'left',
            label: 'currency',
            field: 'currency'
          },
          {
            name: 'key',
            align: 'left',
            label: 'key',
            field: 'key'
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      settingsDialog: {
        show: false,
        data: {}
      },
      formDialog: {
        show: false,
        data: {
          switches: [],
          lnurl_toggle: false,
          show_message: false,
          nostrfy: false,
          show_ack: false,
          show_price: 'None',
          device: 'pos',
          profit: 1,
          amount: 1,
          title: '',
          npub: ''
        }
      },
      qrCodeDialog: {
        show: false,
        data: null
      }
    }
  },
  watch: {
    'formDialog.data.npub': {
      immediate: true,
      handler(newValue) {
        this.formDialog.data.nostrfy = newValue !== ''
      }
    }
  },
  computed: {
    wsMessage() {
      return this.websocketMessage
    }
  },
  methods: {
    openQrCodeDialog(bitcoinswitchId) {
      const bitcoinswitch = _.findWhere(this.bitcoinswitches, {
        id: bitcoinswitchId
      })
      this.qrCodeDialog.data = _.clone(bitcoinswitch)
      this.qrCodeDialog.data.url =
        window.location.protocol + '//' + window.location.host
      this.lnurlValue = this.qrCodeDialog.data.switches[0].lnurl
      this.websocketConnector(
        'wss://' + window.location.host + '/api/v1/ws/' + bitcoinswitchId
      )
      this.qrCodeDialog.show = true
    },
    addSwitch() {
      this.formDialog.data.switches.push({
        amount: 10,
        pin: 0,
        duration: 1000,
        variable: false,
        comment: false
      })
    },
    removeSwitch() {
      this.formDialog.data.switches.pop()
    },
    cancelFormDialog() {
      this.formDialog.show = false
      this.clearFormDialog()
    },
    closeFormDialog() {
      this.clearFormDialog()
      this.formDialog.data = {
        is_unique: false
      }
    },
    sendFormData() {
      if (this.formDialog.data.id) {
        this.updateBitcoinswitch(
          this.g.user.wallets[0].adminkey,
          this.formDialog.data
        )
      } else {
        this.createBitcoinswitch(
          this.g.user.wallets[0].adminkey,
          this.formDialog.data
        )
      }
    },

    createBitcoinswitch(wallet, data) {
      const updatedData = {}
      for (const property in data) {
        if (data[property]) {
          updatedData[property] = data[property]
        }
      }
      LNbits.api
        .request(
          'POST',
          '/bitcoinswitch/api/v1/bitcoinswitch',
          wallet,
          updatedData
        )
        .then(response => {
          this.bitcoinswitches.push(response.data)
          this.formDialog.show = false
          this.clearFormDialog()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    updateBitcoinswitch(wallet, data) {
      const updatedData = {}
      for (const property in data) {
        if (data[property]) {
          updatedData[property] = data[property]
        }
      }
      LNbits.api
        .request(
          'PUT',
          '/bitcoinswitch/api/v1/bitcoinswitch/' + updatedData.id,
          wallet,
          updatedData
        )
        .then(response => {
          this.bitcoinswitches = _.reject(this.bitcoinswitches, function (obj) {
            return obj.id === updatedData.id
          })
          this.bitcoinswitches.push(response.data)
          this.formDialog.show = false
          this.clearFormDialog()
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    getBitcoinswitches() {
      LNbits.api
        .request(
          'GET',
          '/bitcoinswitch/api/v1/bitcoinswitch',
          this.g.user.wallets[0].adminkey
        )
        .then(response => {
          if (response.data.length > 0) {
            this.bitcoinswitches = response.data
          }
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    },
    deleteBitcoinswitch(bitcoinswitchId) {
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this pay link?')
        .onOk(() => {
          LNbits.api
            .request(
              'DELETE',
              '/bitcoinswitch/api/v1/bitcoinswitch/' + bitcoinswitchId,
              this.g.user.wallets[0].adminkey
            )
            .then(() => {
              this.bitcoinswitches = _.reject(
                this.bitcoinswitches,
                function (obj) {
                  return obj.id === bitcoinswitchId
                }
              )
            })
            .catch(function (error) {
              LNbits.utils.notifyApiError(error)
            })
        })
    },
    openUpdateBitcoinswitch(bitcoinswitchId) {
      const bitcoinswitch = _.findWhere(this.bitcoinswitches, {
        id: bitcoinswitchId
      })
      this.formDialog.data = _.clone(bitcoinswitch)
      this.formDialog.show = true
    },
    openBitcoinswitchSettings(bitcoinswitchId) {
      const bitcoinswitch = _.findWhere(this.bitcoinswitches, {
        id: bitcoinswitchId
      })
      this.wslocation =
        'wss://' + window.location.host + '/api/v1/ws/' + bitcoinswitchId
      this.settingsDialog.data = _.clone(bitcoinswitch)
      this.settingsDialog.show = true
    },
    websocketConnector(websocketUrl) {
      if ('WebSocket' in window) {
        const ws = new WebSocket(websocketUrl)
        this.updateWsMessage('Websocket connected')
        ws.onmessage = evt => {
          this.updateWsMessage('Message received: ' + evt.data)
        }
        ws.onclose = () => {
          this.updateWsMessage('Connection closed')
        }
      } else {
        this.updateWsMessage('WebSocket NOT supported by your Browser!')
      }
    },
    updateWsMessage(message) {
      this.websocketMessage = message
    },
    clearFormDialog() {
      this.formDialog.data = {
        lnurl_toggle: false,
        show_message: false,
        show_ack: false,
        show_price: 'None',
        title: ''
      }
    },
    exportCSV() {
      LNbits.utils.exportCSV(
        this.bitcoinswitchTable.columns,
        this.bitcoinswitches
      )
    }
  },
  created() {
    this.getBitcoinswitches()
    this.location = [window.location.protocol, '//', window.location.host].join(
      ''
    )
    this.wslocation = ['wss://', window.location.host].join('')
    LNbits.api
      .request('GET', '/api/v1/currencies')
      .then(response => {
        this.currency = ['sat', 'USD', ...response.data]
      })
      .catch(LNbits.utils.notifyApiError)
  }
})
