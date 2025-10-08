window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      url: window.location.origin + '/bitcoinswitch/api/v1/lnurl',
      apiUrl: window.location.origin + '/bitcoinswitch/api/v1',
      publicUrl: window.location.origin + '/bitcoinswitch/public',
      activeUrl: '',
      activePin: 0,
      lnurl: '',
      filter: '',
      currency: 'sat',
      currencies: [],
      bitcoinswitches: [],
      taprootAssetsAvailable: false,
      availableAssets: [],
      loadingAssets: false,
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
          disposable: true,
          accepts_assets: false,
          accepted_asset_ids: []
        }
      },
      qrCodeDialog: {
        show: false,
        data: null
      }
    }
  },
  computed: {
    cleanLnurl() {
      return this.lnurl?.replace('lightning:', '') || ''
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

      if (!_switch) {
        console.error('No switch found for pin:', this.activePin)
        return
      }

      this.activeUrl = `${this.url}/${this.qrCodeDialog.data.id}?pin=${_switch.pin}`
    },
    openQrCodeDialog(bitcoinswitchId) {
      const bitcoinswitch = _.findWhere(this.bitcoinswitches, {
        id: bitcoinswitchId
      })

      this.qrCodeDialog.data = _.clone(bitcoinswitch)
      this.activePin = bitcoinswitch.switches[0].pin
      this.qrCodeDialog.show = true

      // Manually trigger URL generation since watcher might not fire
      this.generateSwitchUrl()
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
        switches: [],
        lnurl_toggle: false,
        show_message: false,
        show_ack: false,
        show_price: 'None',
        title: '',
        accepts_assets: false,
        accepted_asset_ids: []
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
        switches: [],
        is_unique: false,
        disabled: false,
        disposable: true,
        accepts_assets: false,
        accepted_asset_ids: []
      }
    },
    sendFormData() {
      const processedData = this.processFormData(this.formDialog.data)
      if (this.formDialog.data.id) {
        this.updateBitcoinswitch(processedData)
      } else {
        this.createBitcoinswitch(processedData)
      }
    },

    processFormData(data) {
      // Filter out undefined/null/empty values
      const updatedData = Object.entries(data)
        .filter(([_, value]) => value !== undefined && value !== null && value !== '')
        .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {})

      // Apply global taproot settings if needed
      if (data.accepts_assets && data.switches) {
        updatedData.switches = data.switches.map(sw => ({
          ...sw,
          accepts_assets: true,
          accepted_asset_ids: data.accepted_asset_ids || []
        }))
      }

      return updatedData
    },

    createBitcoinswitch(processedData) {
      LNbits.api
        .request(
          'POST',
          this.apiUrl,
          this.g.user.wallets[0].adminkey,
          processedData
        )
        .then(response => {
          this.bitcoinswitches.push(response.data)
          this.closeFormDialog()
        })
        .catch(error => {
          LNbits.utils.notifyApiError(error)
        })
    },
    updateBitcoinswitch(processedData) {
      LNbits.api
        .request(
          'PUT',
          this.apiUrl + '/' + this.formDialog.data.id,
          this.g.user.wallets[0].adminkey,
          processedData
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

      // Extract global taproot settings
      if (bitcoinswitch.switches?.length > 0) {
        const firstSwitchWithAssets = bitcoinswitch.switches.find(sw => sw.accepts_assets)
        if (firstSwitchWithAssets) {
          this.formDialog.data.accepts_assets = true
          this.formDialog.data.accepted_asset_ids = firstSwitchWithAssets.accepted_asset_ids || []
        } else {
          this.formDialog.data.accepts_assets = false
          this.formDialog.data.accepted_asset_ids = []
        }
      }

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
    },

    // Taproot Assets methods
    handleAcceptAssetsChange(val) {
      if (!val) {
        this.formDialog.data.accepted_asset_ids = []
      }
      // Update all switches to use global setting
      this.formDialog.data.switches.forEach(sw => {
        sw.accepts_assets = val
        sw.accepted_asset_ids = val ? this.formDialog.data.accepted_asset_ids : []
        // Variable amounts not supported for taproot assets
        if (val) {
          sw.variable = false
        }
      })
    },

    async checkTaprootAssetsAvailability() {
      try {
        const response = await LNbits.api.request(
          'GET',
          '/api/v1/extension',
          this.g.user.wallets[0].adminkey
        )

        this.taprootAssetsAvailable = response.data.some(
          ext => ext.code === 'taproot_assets'
        )

        if (this.taprootAssetsAvailable) {
          await this.loadAvailableAssets()
        }
      } catch (error) {
        console.error('Error checking taproot availability:', error)
        this.taprootAssetsAvailable = false
      }
    },

    async loadAvailableAssets() {
      if (!this.taprootAssetsAvailable) return

      this.loadingAssets = true
      try {
        const response = await LNbits.api.request(
          'GET',
          '/taproot_assets/api/v1/taproot/listassets',
          this.g.user.wallets[0].adminkey
        )

        this.availableAssets = response.data.map(asset => ({
          asset_id: asset.asset_id,
          name: asset.name || `Asset ${asset.asset_id.substring(0, 8)}...`,
          balance: asset.balance || 0
        }))
      } catch (error) {
        this.availableAssets = []
      } finally {
        this.loadingAssets = false
      }
    },

    hasTaprootAssets(bitcoinswitch) {
      return bitcoinswitch.switches?.some(s =>
        s.accepts_assets && s.accepted_asset_ids?.length > 0
      )
    },

    getAssetName(assetIdOrObject) {
      // Handle both asset_id string and full asset object
      const assetId = typeof assetIdOrObject === 'string'
        ? assetIdOrObject
        : assetIdOrObject?.asset_id

      if (!assetId) return 'Unknown Asset'

      const asset = this.availableAssets.find(a => a.asset_id === assetId)
      return asset ? asset.name : `${assetId.substring(0, 8)}...`
    }
  },
  created() {
    this.getBitcoinswitches()
    this.checkTaprootAssetsAvailability()
    LNbits.api
      .request('GET', '/api/v1/currencies')
      .then(response => {
        this.currencies = ['sat', 'USD', ...response.data]
      })
      .catch(LNbits.utils.notifyApiError)
  }
})
