# Fotografias públicas — controles de procedência, 07/10/2026

Pasta reservada para duas fotografias publicadas por fonte primária, sem rostos, usadas como controles exploratórios. Origem editorial não é autenticação criptográfica. Não são imagens enviadas por usuários.

Rótulo: `source-published-photo`, não `human-authenticated`, `true` ou `100%-authentic`. Arquivos, hashes e procedência constam no [manifesto](manifest.json). Downloads HTTPS diretos retornaram HTTP 200 e `image/jpeg`; nenhuma transformação local foi aplicada.

Nenhum detector foi executado nesta preparação. Amostra de duas imagens não mede precisão, generalização, clonagem facial nem desempenho em fotografias particulares. Fotografias amplamente publicadas também podem ter aparecido no treinamento dos modelos.

## Origem dos arquivos

| Controle | Arquivo | Crédito | Procedência publicada |
| --- | --- | --- | --- |
| INTERNET-REAL-IMG-01 | `nasa-zinnia-iss046e009018.jpg` | NASA; fotografia associada a Scott Kelly | [Artigo de 19/01/2016](https://www.nasa.gov/image-article/first-flower-grown-space-stations-veggie-facility-2/) sobre a zínia fotografada na ISS. [JPEG vinculado ao artigo](https://www.nasa.gov/wp-content/uploads/2023/03/iss046e009018.jpg). |
| INTERNET-REAL-IMG-02 | `nasa-apollo17-blue-marble-print.jpg` | NASA Johnson Space Center / Earth Science and Remote Sensing Unit; tripulação Apollo 17 | [Registro oficial SVS 30613](https://svs.gsfc.nasa.gov/30613), republicado em 20/07/2015, identifica a fotografia de 07/12/1972 e oferece esta reprodução JPEG 1024×1024. [Arquivo vinculado](https://svs.gsfc.nasa.gov/vis/a030000/a030600/a030613/blue_marble_apollo_17_19721207_print.jpg). |

A inspeção visual local confirmou duas imagens sem rostos: plantas na instalação de cultivo; Terra vista do espaço. Isso não valida toda sua cadeia de custódia.

### Processamento editorial, metadados e limites

- Zínia: JPEG publicado 1041×693; EXIF informa `NIKON D4`, `DateTimeOriginal=2016:01:16 12:16:13` e `Adobe Photoshop CC 2014 (Windows)`. Metadados podem ser alterados. Arquivo não é RAW nem prova de ausência de edição; registrar o editor não basta para concluir montagem ou IA.
- Apollo 17: versão `print` publicada 1024×1024, reprodução digital preparada para apresentação; não é negativo original de câmera. Não confundir este registro de 1972 com os mosaicos posteriores também chamados Blue Marble. Nenhuma composição multiquadro é descrita para a fotografia-fonte neste registro oficial. O histórico editorial completo da reprodução não foi auditado.
- O SHA-256 identifica os bytes baixados nesta rodada, não autentica câmera, cena, alegações associadas ou identidade. Nenhum C2PA foi homologado nesta preparação.
- Conservar os dois controles separados de imagens geradas por IA. Não ajustar limiares para “acertar” estas duas amostras nem adicioná-las silenciosamente ao corpus independente de validação.

## Condições de uso

Uso de controle educacional/informativo fundamentado nas [NASA Media Usage Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/), consultadas em 07/10/2026. Não atribuímos licença CC0/Creative Commons. A política permite uso factual com crédito e sem insinuar endosso, ressalvando materiais de terceiros, marcas e direitos de pessoas. Créditos das páginas selecionadas identificam NASA, sem titular terceiro indicado. A preparação não implica revisão ou aprovação do Verify pela agência. Saídas dos detectores pertencem ao serviço/modelo responsável, não à NASA. Não reutilizar estes arquivos como publicidade, logotipo ou suposto selo de precisão.

## Conferência e próximo teste

Na raiz do checkout:

```bash
sha256sum backend/tests/fixtures/validation/internet-real-2026-10-07/nasa-zinnia-iss046e009018.jpg
sha256sum backend/tests/fixtures/validation/internet-real-2026-10-07/nasa-apollo17-blue-marble-print.jpg
```

Hashes esperados constam no manifesto. Ambos ficam abaixo de 25 MiB e 20 megapixels; não há voz nem teste de deepfake facial. Próxima rodada deve registrar status de cada fornecedor, limitações, tempo e erros pela interface. Não obrigar resposta `Authentic`: ausência de sinal de IA não certifica origem humana. Upload para detector externo envia os bytes a esse fornecedor; respeitar configuração e orçamento autorizados.
