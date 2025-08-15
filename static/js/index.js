window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      tab: 'bech32',
      url: window.location.origin + '/bitcoinswitch/api/v1/lnurl',
      activePin: 0,
      lnurl: '',
      filter: '',
      currency: 'USD',
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
      formDialog: {
        show: false,
        data: {
          switches: [],
          lnurl_toggle: false,
          show_message: false,
          show_ack: false,
          show_price: 'None',
          device: 'pos',
          profit: 1,
          amount: 1,
          title: ''
        }
      },
      qrCodeDialog: {
        show: false,
        data: null
      }
    }
  },
  computed: {
    wsMessage() {
      return this.websocketMessage
    }
  },
  watch: {
    activePin() {
      this.generateSwitchUrl()
    },
    tab() {
      this.generateSwitchUrl()
    }
  },
  methods: {
    generateSwitchUrl() {
      const _switch = this.qrCodeDialog.data.switches.find(
        s => s.pin === this.activePin
      )
      const url = `${this.url}/${this.qrCodeDialog.data.id}?amount=${_switch.amount}&pin=${_switch.pin}&duration=${_switch.duration}&variable=${_switch.variable}&comment=${_switch.comment}`
      if (this.tab == 'bech32') {
        const bytes = new TextEncoder().encode(url)
        const bech32 = NostrTools.nip19.encodeBytes('lnurl', bytes)
        this.lnurl = `lightning:${bech32.toUpperCase()}`
      } else if (this.tab == 'lud17') {
        this.lnurl = url.replace('https://', 'lnurlp://')
      }
    },
    openQrCodeDialog(bitcoinswitchId) {
      const bitcoinswitch = _.findWhere(this.bitcoinswitches, {
        id: bitcoinswitchId
      })
      this.qrCodeDialog.data = _.clone(bitcoinswitch)
      this.activePin = bitcoinswitch.switches[0].pin
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
    copyDeviceString(bitcoinswitchId) {
      const loc = `wss://${window.location.host}/api/v1/ws/${bitcoinswitchId}`
      this.copyText(loc, 'Device string copied to clipboard!')
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
    LNbits.api
      .request('GET', '/api/v1/currencies')
      .then(response => {
        this.currency = ['sat', 'USD', ...response.data]
      })
      .catch(LNbits.utils.notifyApiError)
  }
})
