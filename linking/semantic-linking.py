from allennlp.predictors.predictor import Predictor
predictor = Predictor.from_path("https://storage.googleapis.com/allennlp-public-models/bert-base-srl-2020.03.24.tar.gz")
predictor.predict(
  sentence="Did Uriah honestly think he could beat the game in under three hours?"
)