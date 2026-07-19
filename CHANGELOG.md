# Changelog

## [1.3.0](https://github.com/Skrockle/Essentia-Studio/compare/essentia-studio-v1.2.0...essentia-studio-v1.3.0) (2026-07-19)


### Features

* add CUDA inference pipeline and tuning controls ([5491607](https://github.com/Skrockle/Essentia-Studio/commit/54916077b8f1ec9545451fa0e0b963e48a1b645f))
* add ONNX CUDA development image ([ea2c0e1](https://github.com/Skrockle/Essentia-Studio/commit/ea2c0e12fcd5665544e62b720f292e858465ca65))
* add ONNX CUDA development image ([d50e405](https://github.com/Skrockle/Essentia-Studio/commit/d50e40501a8d5b552fc7d60c43e7c672bb0a7734))
* pipeline CUDA inference across CPU and GPU ([#22](https://github.com/Skrockle/Essentia-Studio/issues/22)) ([58a803e](https://github.com/Skrockle/Essentia-Studio/commit/58a803e141ef3c72faadb0ce638680fa93fbe6c9))


### Bug Fixes

* accept ONNX feature arrays from Essentia ([99d4754](https://github.com/Skrockle/Essentia-Studio/commit/99d475416b34a97daae236f304805b93e4139eff))
* accept ONNX feature arrays from Essentia ([8c2e75d](https://github.com/Skrockle/Essentia-Studio/commit/8c2e75d85539586987bf7902700da45e717048e5))
* apply CPU worker setting to analysis jobs ([bdd66cf](https://github.com/Skrockle/Essentia-Studio/commit/bdd66cfb75116fcb9ce6cacbe0f081aaa4736c12))
* apply CPU worker setting to analysis jobs ([8c2accf](https://github.com/Skrockle/Essentia-Studio/commit/8c2accffe5bc08adae3e14571bdeec75d90365f3))
* correct ONNX model checksums ([60a79f9](https://github.com/Skrockle/Essentia-Studio/commit/60a79f94ee3b013d28728f7d3e2506ea8e454d9f))
* correct ONNX model metadata hash ([06772eb](https://github.com/Skrockle/Essentia-Studio/commit/06772eb05e37857c35ab5b1d59b23e8082c72739))
* correct ONNX model metadata hash ([de5e7be](https://github.com/Skrockle/Essentia-Studio/commit/de5e7be2ae0b89362c499f9791ce697ab80dcf7b))
* include ONNX manifest in model directory ([9aba71f](https://github.com/Skrockle/Essentia-Studio/commit/9aba71f75db45e4b6055b9a3a411e7f24e9073af))
* include ONNX manifest in model directory ([652077e](https://github.com/Skrockle/Essentia-Studio/commit/652077ec8e44d9667d09b76df02007ae49bda815))
* prevent CUDA classification memory failures ([#21](https://github.com/Skrockle/Essentia-Studio/issues/21)) ([56cf1be](https://github.com/Skrockle/Essentia-Studio/commit/56cf1be551f3bec18cb64388262746edd9807477))
* rebuild ONNX image models without cache ([66b39a9](https://github.com/Skrockle/Essentia-Studio/commit/66b39a97454df8da4814397b9c0ae9ee29b1f1b8))
* rebuild ONNX image models without cache ([b659b15](https://github.com/Skrockle/Essentia-Studio/commit/b659b151106cf893b2867b1488ca7662df621fde))
* resume active jobs after restart ([b2f4157](https://github.com/Skrockle/Essentia-Studio/commit/b2f4157a181d18a94d52fef9f7c448c3723e6f0d))
* show ONNX model hash details ([66c91bb](https://github.com/Skrockle/Essentia-Studio/commit/66c91bb0649eec79b299caddbebe38b3ab7d4505))
* spawn CUDA inference workers safely ([9ccf7e8](https://github.com/Skrockle/Essentia-Studio/commit/9ccf7e8c75c0c0f0963723b64e2b78aac80ad2da))
* stop analysis jobs promptly on cancel ([9cd131c](https://github.com/Skrockle/Essentia-Studio/commit/9cd131ce7508b945ea286e84ea4746e368684d89))
* use verified model archive for ONNX image ([ab40e1d](https://github.com/Skrockle/Essentia-Studio/commit/ab40e1deb1769ebe8a7b479f3a6d54da872bbf38))
* use verified model archive for ONNX image ([1d479f0](https://github.com/Skrockle/Essentia-Studio/commit/1d479f0dc6bfe02b68c43081e5208f7bc0a3ca7c))
* validate all ONNX model hashes during build ([42e0756](https://github.com/Skrockle/Essentia-Studio/commit/42e07565533ef2452c37a673e902e5fc9506fe2f))
* validate all ONNX model hashes during build ([0b9df4a](https://github.com/Skrockle/Essentia-Studio/commit/0b9df4a0a2b8704c87ed67ffed2877da9b85ef2d))


### Performance Improvements

* batch CUDA classification heads ([a16b8e7](https://github.com/Skrockle/Essentia-Studio/commit/a16b8e737b21948ff852df34be918ee3ddf38d91))
* batch CUDA classification heads ([ada6552](https://github.com/Skrockle/Essentia-Studio/commit/ada6552e425600366592aa609828719573586da8))

## [1.2.0](https://github.com/Skrockle/Essentia-Studio/compare/essentia-studio-v1.1.0...essentia-studio-v1.2.0) (2026-07-18)


### Features

* add job monitor and dev image workflow ([e7bf8c1](https://github.com/Skrockle/Essentia-Studio/commit/e7bf8c103f8aefedc3b9af324aede65cca360c7b))


### Bug Fixes

* cancel jobs and stabilize status bar ([024232a](https://github.com/Skrockle/Essentia-Studio/commit/024232a2c1041ca49fedf78e14b03f2b196fab55))

## [1.1.0](https://github.com/Skrockle/Essentia-Studio/compare/essentia-studio-v1.0.0...essentia-studio-v1.1.0) (2026-07-17)


### Features

* add persistent accessible themes ([b92d972](https://github.com/Skrockle/Essentia-Studio/commit/b92d97268ead08548d8e907f7903d2d3e7a4c8c7))
* add resource benchmark interface ([e7a96b5](https://github.com/Skrockle/Essentia-Studio/commit/e7a96b511ff3b0692d7fc19a24115525498b6d63))
* add tag suggestion combobox ([978d2fe](https://github.com/Skrockle/Essentia-Studio/commit/978d2fefe92293eac2792d0a03cbbf78fa2ab9f7))
* apply benchmark worker recommendations ([07ecc54](https://github.com/Skrockle/Essentia-Studio/commit/07ecc54257fc1bf1f9772a38724c24d932c97932))
* automate metadata analysis and benchmark resources ([e3cce6f](https://github.com/Skrockle/Essentia-Studio/commit/e3cce6fc0bba154e2ba75c8159324d542edaab43))
* automate new and changed tracks ([fe33904](https://github.com/Skrockle/Essentia-Studio/commit/fe339042cea1a796872d3951cc126cb8f81f5af0))
* configure watcher and automation schedule ([a57960a](https://github.com/Skrockle/Essentia-Studio/commit/a57960aec4f212648a84e7895d8bd81055887b83))
* detect container resources for benchmark ([26d0b06](https://github.com/Skrockle/Essentia-Studio/commit/26d0b06a601a83afc2a45fe4089c35db526823ad))
* explain analysis settings and models ([6d3f029](https://github.com/Skrockle/Essentia-Studio/commit/6d3f0290b679162b9322717fa89c0c17f89f6a89))
* expose benchmark jobs and results ([907890c](https://github.com/Skrockle/Essentia-Studio/commit/907890c259b537028ee21148762452bd5ffc98b8))
* expose model-backed tag options ([69581bc](https://github.com/Skrockle/Essentia-Studio/commit/69581bcf8c3963635202b6028e25d34c91cf4e69))
* load settings from yaml and environment ([cd7f33e](https://github.com/Skrockle/Essentia-Studio/commit/cd7f33e8760de233da4db506ba7c044c8d5502a7))
* load tag options in the workbench ([71017dd](https://github.com/Skrockle/Essentia-Studio/commit/71017ddd53ee2bbcb0f299f7c6d57c11bdd5f7c8))
* persist benchmark measurements ([5f3642a](https://github.com/Skrockle/Essentia-Studio/commit/5f3642a3836a161fcb3da1a3cc7b1c3f24fc58ef))
* persist scanned track metadata ([7b4f95d](https://github.com/Skrockle/Essentia-Studio/commit/7b4f95d04823d94be349d7822fd4fedc4f332bc0))
* persist settings yaml atomically ([3eb3129](https://github.com/Skrockle/Essentia-Studio/commit/3eb3129dd91098d2143954d174d45414d2983faf))
* persist structured job item errors ([f29a932](https://github.com/Skrockle/Essentia-Studio/commit/f29a932b62917ee341a2c8d4f0591fd4afa85398))
* persist workbench filters and columns ([5e51182](https://github.com/Skrockle/Essentia-Studio/commit/5e5118291d40a111c0b6ac3bf8a4529681f86ffa))
* run isolated analysis benchmark ([eff060c](https://github.com/Skrockle/Essentia-Studio/commit/eff060c4b1810ea5637fc1272a7b896a4fa806f5))
* run tag writes as observable jobs ([937f67a](https://github.com/Skrockle/Essentia-Studio/commit/937f67a2cdc60ac40d9938a91b59855beea2308f))
* show current track metadata and state ([72a0b92](https://github.com/Skrockle/Essentia-Studio/commit/72a0b928b8415fa7c7f798685780c22e412a71f1))
* show live analysis and write progress ([edf3d67](https://github.com/Skrockle/Essentia-Studio/commit/edf3d67e885c4bbc8ced3ce0b7a2df6797a4fe54))
* show uncertain genre suggestions explicitly ([dba6a97](https://github.com/Skrockle/Essentia-Studio/commit/dba6a97abf6a24ae76f5a445fc36eb5d53c93d27))
* split hierarchical genre predictions ([fa89c96](https://github.com/Skrockle/Essentia-Studio/commit/fa89c96a62f8a6846a5a7c7ce620bb3cc17b523f))
* validate automation schedules ([4e7cfee](https://github.com/Skrockle/Essentia-Studio/commit/4e7cfeef97e297e88b3a7aacbc7e9dfc66288b0e))
* watch stable audio files ([2e7bfae](https://github.com/Skrockle/Essentia-Studio/commit/2e7bfae20e2428f754c1b8a01be3ebd207954494))


### Bug Fixes

* add verified model archive fallback ([75a07a1](https://github.com/Skrockle/Essentia-Studio/commit/75a07a176cc50b994038a389732f05e8bd05954c))
* complete dark theme and table dividers ([63ba7b5](https://github.com/Skrockle/Essentia-Studio/commit/63ba7b5867327fedb4df066e4db946592d79b710))
* constrain tag suggestions to viewport ([a95b5dd](https://github.com/Skrockle/Essentia-Studio/commit/a95b5dd88534929ecc4154893f160d97bc351222))
* enforce visible genre suggestion limits ([b2533ff](https://github.com/Skrockle/Essentia-Studio/commit/b2533ff17e3ff6ed39e8781677d7c3885797876a))
* expose scanned library for analysis ([066c7ad](https://github.com/Skrockle/Essentia-Studio/commit/066c7adc4a9d54cb27470965ae27936a53de875f))
* harden tag catalog normalization ([7eecebe](https://github.com/Skrockle/Essentia-Studio/commit/7eecebe32a440834f0553f3004946a3a13738896))
* keep table menus readable and exclusive ([e169693](https://github.com/Skrockle/Essentia-Studio/commit/e16969360a1991f6ebefb7fbb0f9049f1953212d))
* log recoverable analysis worker crashes ([a9f20e8](https://github.com/Skrockle/Essentia-Studio/commit/a9f20e891db43b32d1cba7eeacc3f8e854aac13c))
* make tag suggestions fully usable ([38941c9](https://github.com/Skrockle/Essentia-Studio/commit/38941c95597b054fa14df5402c0145124addffb6))
* present analysis thresholds as percentages ([9e9b771](https://github.com/Skrockle/Essentia-Studio/commit/9e9b77153b8805b43742dc57bb429e2b434cb74a))
* preserve tag input focus ([7fcb1bb](https://github.com/Skrockle/Essentia-Studio/commit/7fcb1bb5b6925ed25e1af51dab1c5c890741e7cf))
* reconcile legacy hierarchical genre drafts ([bcad5fe](https://github.com/Skrockle/Essentia-Studio/commit/bcad5fed1a241b0f6de54c967ecfd9a49583bc55))
* reconcile verified write state ([7e9fe74](https://github.com/Skrockle/Essentia-Studio/commit/7e9fe747fcba1e93295a8c8b8ab277e81e584415))
* recover terminated analysis workers ([818a2cd](https://github.com/Skrockle/Essentia-Studio/commit/818a2cdc874233717108b13aac3eac806f371dd0))
* reopen tag suggestions on click ([11b47d5](https://github.com/Skrockle/Essentia-Studio/commit/11b47d56822af5ed2b332b1d385eeea31f2d7a02))
* restore windows and browser ci ([1d57d60](https://github.com/Skrockle/Essentia-Studio/commit/1d57d60bf5227111778aeec77d8a4a4eb612bffe))
* separate uncertain genre evidence from drafts ([a6cb393](https://github.com/Skrockle/Essentia-Studio/commit/a6cb39357bf891d17d8fc1e91595e32556cf9c03))
* stabilize tag combobox suggestions ([6bdbbdb](https://github.com/Skrockle/Essentia-Studio/commit/6bdbbdbd9d6b268e992800355b9e77ae10d2b532))
* theme all workbench surfaces in dark mode ([857a3d6](https://github.com/Skrockle/Essentia-Studio/commit/857a3d635ff8abf019b3ce0b8556c3ae4179c306))

## 1.0.0 (2026-07-16)


### Features

* add analysis review workbench ([acc7db5](https://github.com/Skrockle/Essentia-Studio/commit/acc7db5327aafb1e6d7e66f824b0ca6fdf053d46))
* add application health and settings api ([8a49f6f](https://github.com/Skrockle/Essentia-Studio/commit/8a49f6f6ba6916c54581e4d44bc0cb288808893c))
* add complete smart playlist studio ([c4544cd](https://github.com/Skrockle/Essentia-Studio/commit/c4544cd1d0c3f4b3a254508a88cfaa000d3f8aae))
* add Essentia analysis jobs ([f21c82d](https://github.com/Skrockle/Essentia-Studio/commit/f21c82d85fb020e9e425b7de212556812a49407b))
* add persisted job coordinator ([22582c7](https://github.com/Skrockle/Essentia-Studio/commit/22582c7993a6754085f63371e92e66c2c5718baf))
* add studio application shell ([22cf4e8](https://github.com/Skrockle/Essentia-Studio/commit/22cf4e89cf0c546daa8c2fc86880b4c73696f1dc))
* add verified tag writes and undo ([7d697ed](https://github.com/Skrockle/Essentia-Studio/commit/7d697eda0aca625d015c8e38342ae04b6b1bca6b))
* complete analysis workbench workflow ([4d486ac](https://github.com/Skrockle/Essentia-Studio/commit/4d486acd313e4ce2cbf807c90135c98ab72a2793))
* expose smart playlist api ([dda681d](https://github.com/Skrockle/Essentia-Studio/commit/dda681dfacf962baf77715f29b5e090f1a578fae))
* import complete Navidrome playlist catalog ([2d70a96](https://github.com/Skrockle/Essentia-Studio/commit/2d70a9645aa5395649f31c2dd3b80d1bc1d66289))
* package CPU and NVIDIA CUDA images ([e360dc6](https://github.com/Skrockle/Essentia-Studio/commit/e360dc616c76f2fdf08395a3efbcd72717313303))
* persist application settings ([00f9500](https://github.com/Skrockle/Essentia-Studio/commit/00f9500d25fda4a8f9b523cd40c54edd4bd19656))
* persist smart playlists atomically ([f4848fa](https://github.com/Skrockle/Essentia-Studio/commit/f4848faa28884422218d6c409f0bcf39f4c5cfc8))
* scaffold cross-platform application ([9e515ea](https://github.com/Skrockle/Essentia-Studio/commit/9e515ea5ea87a1b791f44c99f4605e0bb8ffea30))
* scan mounted music library safely ([95adcbc](https://github.com/Skrockle/Essentia-Studio/commit/95adcbc9a17af2298af8577ec65a619101d6cfcc))
* validate and build smart playlists ([410e993](https://github.com/Skrockle/Essentia-Studio/commit/410e993da4505c07006628d35bce66489c3662f9))


### Bug Fixes

* allow CI container to update fixture tags ([4e83493](https://github.com/Skrockle/Essentia-Studio/commit/4e834936da5cd1420d8bd076d09a9e2dbaed845a))
* keep runtime models readable ([c8e9ec3](https://github.com/Skrockle/Essentia-Studio/commit/c8e9ec3cec6b84259c1b6e3baeb3b20a266cacf5))

## Changelog

All notable changes to Essentia Studio are maintained automatically by
[Release Please](https://github.com/googleapis/release-please) from Conventional
Commits.
