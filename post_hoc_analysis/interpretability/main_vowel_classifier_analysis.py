"""
This script is used to analyze the weights of the vowel classifier (bias=False).
- weights are logged as a table to wandb
- weights are plotted as a heatmap
- the most important dimensions for each vowel are found and plotted
- the predictions of the classifier are plotted in a 2D space

Warning: script only for VOWEL classifier (bias=False)!! The script is only used for latent space analysis.
"""

# Example: temp sim_audio_de_wwww_distr_true --overrides syllables_classifier_config.encoder_num=9


import matplotlib.pyplot as plt
import numpy as np
import torch
import wandb

from arg_parser import arg_parser
from config_code.config_classes import OptionsConfig
from models import load_audio_model
from models.loss_supervised_syllables import Syllables_Loss
from options import get_options
from utils.utils import retrieve_existing_wandb_run_id, rescale_between_neg1_and_1, get_audio_classific_key, \
    get_nb_classes, get_classif_log_path


def plot_weights(opt: OptionsConfig, weights: np.ndarray, wandb, first_dim: int = 1):
    # heatmap using matplotlib
    fig, ax = plt.subplots()
    im = ax.imshow(weights, cmap="binary")
    # template options: https://matplotlib.org/stable/gallery/color/colormap_reference.html

    # "a" if number == 0,  "i" if number == 1 else "u"

    # We want to show all ticks...
    ax.set_xticks(np.arange(len(weights[0])))
    ax.set_yticks(np.arange(len(weights)))
    # ... and label them with the respective list entries

    ax.set_xticklabels(np.arange(len(weights[0])) + first_dim)  # starts at 1

    # ax.set_yticklabels(np.arange(len(weights)))
    # set y tick labels to be the vowels
    ax.set_yticklabels(["a", "i", "u"])

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(),
             rotation_mode="anchor"
             )

    # # Loop over data dimensions and create text annotations.
    for i in range(len(weights)):
        for j in range(len(weights[0])):
            text = ax.text(j, i, round(weights[i, j], 2),  # bold=True, fontsize=14,
                           ha="center", va="center", color="black",
                           bbox=dict(boxstyle="round", facecolor="white", edgecolor="white",
                                     alpha=0.5))  # transparent edge color
            # color options: https://matplotlib.org/stable/gallery/color/named_colors.html

    # change size
    fig.set_size_inches(18.5, 10.5)
    fig.tight_layout()

    ax.set_title("Vowel Classifier Weights")
    fig.tight_layout()

    # title size
    ax.title.set_size(26)

    # x, y labels
    ax.set_xlabel("Dimension", fontsize=20)
    ax.set_ylabel("Vowel", fontsize=20)

    # tight layout
    fig.tight_layout()

    # save as pdf
    save_dir = opt.log_path
    pdf_path = f"{save_dir}/vowel_classifier_weights_{first_dim}.pdf"
    png_path = f"{save_dir}/vowel_classifier_weights_{first_dim}.png"
    plt.savefig(f"{save_dir}/vowel_classifier_weights_{first_dim}.pdf")
    plt.savefig(png_path)

    return png_path


def _get_predictions(classifier, device, n_features, dim1, dim2):
    # DIM1, DIM2 ARE ZERO BASED
    t = 100
    min, max = -3, 3
    range = np.linspace(min, max, t)
    z = torch.zeros((1, n_features)).to(device)

    # data = np.array([])
    data = np.zeros((t, t, 3))
    for i, val_i in enumerate(range):
        for j, val_j in enumerate(range):
            z[0][dim1] = val_i
            z[0][dim2] = val_j

            prediction = classifier(z).detach().cpu().numpy()  # (1, 3)
            # softmax
            prediction = np.exp(prediction) / np.exp(prediction).sum(axis=1, keepdims=True)
            data[i][j] = prediction[0]

    return data, range


def plot_label_space(opt: OptionsConfig, wandb, classifier, n_features, dim1, dim2):  # dim1, dim2 are zero based
    fig, ax = plt.subplots()
    predictions, range = _get_predictions(classifier, opt.device, n_features, dim1, dim2)
    im = ax.imshow(predictions)

    # x and y ticks are the values between `min` and `max`
    ax.set_xticks(np.arange(len(range)))
    ax.set_yticks(np.arange(len(range)))

    # round to 2 decimals
    ax.set_xticklabels(np.round(range, 2))
    ax.set_yticklabels(np.round(range, 2))

    # reduce the number of ticks
    ax.xaxis.set_major_locator(plt.MaxNLocator(7))
    ax.yaxis.set_major_locator(plt.MaxNLocator(10))

    # title
    ax.set_title("Vowel Classifier Weights")

    # x, y labels
    ax.set_xlabel(f"Dimension: {dim1 + 1}")
    ax.set_ylabel(f"Dimension: {dim2 + 1}")

    # orde: a, i, u --> red: a, green: i, blue: u

    # Add legend
    # https://matplotlib.org/stable/gallery/text_labels_and_annotations/custom_legends.html
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], marker='s', color='w', label='a', markerfacecolor='r', markersize=15),
                       Line2D([0], [0], marker='s', color='w', label='i', markerfacecolor='g', markersize=15),
                       Line2D([0], [0], marker='s', color='w', label='u', markerfacecolor='b', markersize=15)]

    ax.legend(handles=legend_elements, loc='lower right')

    # save to pdf
    save_dir = opt.log_path
    plt.savefig(f"{save_dir}/vowel_classifier_weights_heatmap.pdf")
    plt.savefig(f"{save_dir}/vowel_classifier_weights_heatmap.png")

    if opt.use_wandb:
        wandb_section = get_audio_classific_key(opt, bias=False)
        wandb.log({f"{wandb_section}/Vowel Classifier Weights Heatmap": [
            wandb.Image(f"{save_dir}/vowel_classifier_weights_heatmap.png")]})


def main():
    opt: OptionsConfig = get_options()
    bias = opt.syllables_classifier_config.bias

    assert not bias, "This script is only for the vowel classifier (bias=False)!!"
    assert opt.syllables_classifier_config.dataset.labels == "vowels", "This script is only for the vowel classifier!!"

    if opt.use_wandb:
        run_id, project_name = retrieve_existing_wandb_run_id(opt)
        wandb.init(id=run_id, resume="allow", project=project_name, entity=opt.wandb_entity)

    # MUST HAPPEN AFTER wandb.init
    classifier_config = opt.syllables_classifier_config
    classif_module: int = classifier_config.encoder_module
    classif_layer: int = classifier_config.encoder_layer
    classif_path = get_classif_log_path(classifier_config, classif_module, classif_layer, bias, deterministic_encoder=opt.encoder_config.deterministic)
    arg_parser.create_log_path(
        opt, add_path_var=classif_path)
    context_model, _ = load_audio_model.load_model_and_optimizer(
        opt,
        opt.syllables_classifier_config,
        reload_model=True,
        calc_accuracy=True,
        num_GPU=1,
    )

    # the classifier is a part of the loss function
    n_labels = get_nb_classes(classifier_config.dataset.dataset, classifier_config.dataset.labels)

    n_features = opt.encoder_config.architecture.modules[0].cnn_hidden_dim
    syllables_loss = Syllables_Loss(opt, hidden_dim=n_features, calc_accuracy=True, bias=False, num_syllables=n_labels)

    # Load the trained model
    model_path = opt.log_path + '/model_0.ckpt'
    syllables_loss.load_state_dict(torch.load(model_path))

    # Load a few data points
    context_model.eval()

    linear_classifier = syllables_loss.linear_classifier
    linear_classifier.eval()

    weights_and_biases = list(linear_classifier.parameters())
    assert len(
        weights_and_biases) == 1, f"The classifier also has a bias term, which is not supported here. len(temp)={len(weights_and_biases)}"
    weights = weights_and_biases[0].detach().cpu().numpy()
    assert weights.shape == (n_labels, n_features)

    # axis=1 because we want to rescale each row (vowel) separately
    weights = rescale_between_neg1_and_1(weights, axis=1)
    weights = weights.T  # (dimensions, labels)

    # there seemed to be some problems with wandb so as a backup we save the weights as a numpy file as well
    np.save(f"{opt.log_path}/vowel_classifier_weights.npy", weights)
    # also as csv
    np.savetxt(f"{opt.log_path}/vowel_classifier_weights.csv", weights, delimiter=",")

    if opt.use_wandb:
        wandb_section = get_audio_classific_key(opt, bias)
        # Log weights as a table (256 rows, 3 columns)
        wandb.log({f"{wandb_section}/Vowel Classifier Weights tbl":
                       wandb.Table(data=weights, columns=[f"label_{i}" for i in range(n_labels)])})

    # I broke this code by transposing the weights, but the code below is not used anymore

    # # find most important dimensions for each vowel
    # _w = np.abs(weights)
    # # sum over all vowels
    # _w = _w.sum(axis=0)
    #
    # # sort
    # _w = np.argsort(_w)
    # # take first 2 dims
    # dim1, dim2 = _w[:2]
    #
    # if opt.use_wandb:
    #     wandb_section = get_audio_classific_key(opt, bias)
    #     # log the most important 32 dimensions and their weights (_w[:32])
    #     wandb.log({f"{wandb_section}/Most important dimensions":
    #                    wandb.Table(data=weights[:, _w[:32]], columns=[f"dim_{i}" for i in _w[:32]])})
    #
    # # plot 32 dimensions at a time
    # ims = []
    # for i in range(0, n_features, 32):
    #     im_path = plot_weights(opt, weights[:, i:i + 32], wandb, first_dim=i + 1)
    #     ims.append(im_path)
    #
    # if opt.use_wandb:
    #     wandb_section = get_audio_classific_key(opt, bias)
    #     wandb.log({f"{wandb_section}/Vowel Classifier Weights imgs": [
    #         wandb.Image(im) for im in ims]})

    # plot_label_space(opt, wandb, linear_classifier, n_features, dim1, dim2)

    if opt.use_wandb:
        wandb.finish()


if __name__ == "__main__":
    main()
