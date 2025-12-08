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
  created() {
    const bsId = this.$route.params.id
    this.url = `${window.location.origin}/bitcoinswitch/api/v1/lnurl/${bsId}`
    LNbits.api
      .request('GET', `/bitcoinswitch/api/v1/public/${bsId}`)
      .catch(LNbits.utils.notifyApiError)
      .then(res => {
        this.bitcoinswitch = res.data
        this.activeSwitch = this.bitcoinswitch.switches[0]
        this.activeUrl = `${this.url}?pin=${this.activeSwitch.pin}`
      })
  }
}
