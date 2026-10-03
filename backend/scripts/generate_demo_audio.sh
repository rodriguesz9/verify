#!/bin/sh
# Run in an isolated container with espeak-ng installed. Both voices synthetic.
set -eu
demo_audio_output=${1:?Provide explicit output directory}
test -d "$demo_audio_output"
espeak-ng -v pt-br -s 145 -w "$demo_audio_output/demo-pedido-sintetico.wav" 'Mãe, caí na rua e perdi meu celular. Faz um Pix urgente para o guincho, por favor.'
espeak-ng -v pt-br -s 145 -w "$demo_audio_output/demo-conversa-sintetica.wav" 'Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café.'
