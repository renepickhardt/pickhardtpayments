## Presentations Slides & Podcasts:
* There is a [slide deck of my presentation of MITBitcoinExpo 2022](https://docs.google.com/presentation/d/1jEf7kQ_xKgFOEDCCbZc-FtZb7UMELdTlpgZhhkAnm74/edit) and the [video can be found on their website](https://www.mitbitcoinexpo.org/) (Track A, Day 2 Timecode: 1:16:19)
* Sydney Socratic Seminar: https://rumble.com/vqearw-optimally-reliable-and-cheap-payment-flows-on-the-lightning-network.html
* Stefan Richter's presentation: https://bitcointv.com/w/383d2113-7c66-47fb-b1e0-b4b4b44a56de (and my version at Lightning Hackday IST: https://youtu.be/IXbWwPiwJLY?t=7774)
* Show on Stephan Livera's Podcast: https://stephanlivera.com/episode/361/
* Intro to min cost flows by David Kager: https://www.youtube.com/watch?v=i0q-Irlf4y4&list=PLaRKlIqjjguDXlnJWG2T7U52iHZl8Edrc

## Scientific resources: 
* Optimally reliable payment flows: https://arxiv.org/abs/2107.05322
* Probabilistic payment delivery: https://arxiv.org/abs/2103.08576
* Piecewise linearization: https://lists.linuxfoundation.org/pipermail/lightning-dev/2022-March/003510.html
* Proof that Piecewise linearization is a good strategy: https://hochbaum.ieor.berkeley.edu/files/ieor290-G.pdf (In general Dorit Hochbaum has a lot of useful lecture notes)
* Pruning the problem: https://github.com/renepickhardt/mpp-splitter/issues/12 (and issues arising from it)
* A glossary and a well documented notebook with some outputs can be found at: https://github.com/renepickhardt/mpp-splitter/blob/pickhardt-payments-simulation-dev/Pickhardt-Payments-Simulation.ipynb
* https://mitmgmtfaculty.mit.edu/jorlin/network-flows/
* Most comprehensive source of original information is probably at: https://www.mit.edu/~dimitrib/home.html (The work body of Dimitri Bertsekas is truely impressive)

## LN implementations doing related stuff: 
* https://github.com/C-Otto/lnd-manageJ/issues/6 (currently closest to being usable on mainnet, see [documentation](https://github.com/C-Otto/lnd-manageJ/blob/main/PickhardtPayments.md))
* https://medium.com/blockstream/c-lightning-v0-10-2-bitcoin-dust-consensus-rule-33e777d58657 (c-lightning integration)
* https://github.com/lightningdevkit/rust-lightning/pull/1227 (LDK has probabilistic payments with uncertainty )
* https://github.com/ACINQ/eclair/pull/2071#pullrequestreview-941902333 (Eclair does similar stuff like our uncertainty network)
* https://github.com/lightningdevkit/rust-lightning/issues/1170#issuecomment-972396747 
* https://github.com/lightningnetwork/lnd/issues/5988 (lnd wants to include some of the results)
* https://github.com/ElementsProject/lightning/issues/4920 (Proposal for Uncertainty Network)
* https://github.com/lightningnetwork/lnd/issues/5988 (add probabilistic path finding)
* https://github.com/lightningnetwork/lnd/issues/5746 (add MPP API)
* https://github.com/lightningnetwork/lnd/issues/4203 (add optimal splitting / payment flows)

## Other: 
Summary by Rusty: https://twitter.com/rusty_twit/status/1519547447324086272 
