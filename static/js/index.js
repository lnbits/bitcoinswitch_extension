window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      url: window.location.origin + '/bitcoinswitch/api/v1/lnurl',
      apiUrl: window.location.origin + '/bitcoinswitch/api/v1',
      publicUrl: window.location.origin + '/bitcoinswitch/public',
      activeUrl: 0,
      activePin: 0,
      lnurl: '',
      filter: '',
      currency: 'sat',
      currencies: [],
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
            name: 'disabled',
            align: 'left',
            label: 'disabled',
            field: 'disabled'
          },
          {
            name: 'disposable',
            align: 'left',
            label: 'disposable',
            field: 'disposable'
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
          title: '',
          disabled: false,
          disposable: true
        }
      },
      qrCodeDialog: {
        show: false,
        data: null
      }
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
    openLink(id) {
      window.open(`${this.publicUrl}/${id}`, '_blank')
    },
    switchLabel(_switch) {
      const label = _switch.label !== null ? _switch.label : 'Switch '
      return label + ' pin: ' + _switch.pin + ' (' + _switch.duration + ' ms)'
    },
    generateSwitchUrl() {
      const _switch = this.qrCodeDialog.data.switches.find(
        s => s.pin === this.activePin
      )
      this.activeUrl = `${this.url}/${this.qrCodeDialog.data.id}?pin=${_switch.pin}`
    },
    openQrCodeDialog(bitcoinswitchId) {
      const bitcoinswitch = _.findWhere(this.bitcoinswitches, {
        id: bitcoinswitchId
      })
      this.qrCodeDialog.data = _.clone(bitcoinswitch)
      this.activePin = bitcoinswitch.switches[0].pin
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
    clearFormDialog() {
      this.formDialog.data = {
        lnurl_toggle: false,
        show_message: false,
        show_ack: false,
        show_price: 'None',
        title: ''
      }
    },
    cancelFormDialog() {
      this.formDialog.show = false
      this.clearFormDialog()
    },
    closeFormDialog() {
      this.clearFormDialog()
      this.formDialog.show = false
      this.formDialog.data = {
        is_unique: false,
        disabled: false,
        disposable: true
      }
    },
    sendFormData() {
      if (this.formDialog.data.id) {
        this.updateBitcoinswitch()
      } else {
        this.createBitcoinswitch()
      }
    },

    createBitcoinswitch() {
      LNbits.api
        .request(
          'POST',
          this.apiUrl,
          this.g.user.wallets[0].adminkey,
          this.formDialog.data
        )
        .then(response => {
          this.bitcoinswitches.push(response.data)
          this.closeFormDialog()
        })
        .catch(error => {
          LNbits.utils.notifyApiError(error)
        })
    },
    updateBitcoinswitch() {
      LNbits.api
        .request(
          'PUT',
          this.apiUrl + '/' + this.formDialog.data.id,
          this.g.user.wallets[0].adminkey,
          this.formDialog.data
        )
        .then(response => {
          const index = this.bitcoinswitches.findIndex(
            obj => obj.id === response.data.id
          )
          this.bitcoinswitches[index] = response.data
          this.$q.notify({
            type: 'success',
            message: 'Bitcoinswitch updated successfully!'
          })
          this.closeFormDialog()
        })
        .catch(LNbits.utils.notifyApiError)
    },
    getBitcoinswitches() {
      LNbits.api
        .request('GET', this.apiUrl, this.g.user.wallets[0].adminkey)
        .then(response => {
          if (response.data.length > 0) {
            this.bitcoinswitches = response.data
          }
        })
        .catch(LNbits.utils.notifyApiError)
    },
    deleteBitcoinswitch(bitcoinswitchId) {
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this pay link?')
        .onOk(() => {
          LNbits.api
            .request(
              'DELETE',
              this.apiUrl + '/' + bitcoinswitchId,
              this.g.user.wallets[0].adminkey
            )
            .then(() => {
              this.bitcoinswitches = _.reject(
                this.bitcoinswitches,
                obj => obj.id === bitcoinswitchId
              )
            })
            .catch(LNbits.utils.notifyApiError)
        })
    },
    triggerPin() {
      const _id = this.qrCodeDialog.data.id
      LNbits.api
        .request(
          'PUT',
          `${this.apiUrl}/trigger/${_id}/${this.activePin}`,
          this.g.user.wallets[0].adminkey
        )
        .then(() => {
          this.$q.notify({
            type: 'positive',
            message: 'Switch triggered successfully!'
          })
        })
        .catch(LNbits.utils.notifyApiError)
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
        this.currencies = ['sat', 'USD', ...response.data]
      })
      .catch(LNbits.utils.notifyApiError)
  }
})
