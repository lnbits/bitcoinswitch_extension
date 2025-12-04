window.PageBitcoinswitchPublic = {
  template: '#page-bitcoinswitch-public',
  mixins: [window.windowMixin],
  data() {
    return {
      bitcoinswitch: null,
      url: '',
      lnurl: '',
      activeUrl: '',
      activeSwitch: null
    }
  },
  watch: {
    activeSwitch(val) {
      this.activeUrl = `${this.url}?pin=${val.pin}`
    }
  },
  async created() {
    const bsId = this.$route.params.id
    this.url = `${window.location.origin}/bitcoinswitch/api/v1/lnurl/${bsId}`
    try {
      const res = await LNbits.api.request(
        'GET',
        `/bitcoinswitch/api/v1/${bsId}`
      )
      this.bitcoinswitch = res.data
    } catch (error) {
      LNbits.utils.notifyApiError(error)
      return
    }
    this.activeSwitch = this.bitcoinswitch.switches[0]
    this.activeUrl = `${this.url}?pin=${this.activeSwitch.pin}`
  }
}
