// edit_quiz.js

function addNewQuestion() {
    // Clone the template for new questions
    var template = document.getElementById('newQuestionTemplate');
    var newQuestion = template.cloneNode(true);
    newQuestion.style.display = 'block'; // Ensure it's visible

    // Generate a unique ID for the new question
    var questionId = Date.now(); // Example of generating a unique ID, adjust as needed

    // Update IDs and names of elements within the new question container
    newQuestion.id = 'question' + questionId;

    // Append the new question to the container
    var newQuestionsContainer = document.getElementById('newQuestionsContainer');
    newQuestionsContainer.appendChild(newQuestion);

    // Show the new question form
    newQuestion.querySelector('.container.question-container').style.display = 'block';

    // Initialize form submission for new question
    var form = document.createElement('form');
    form.style.display = 'none'; // Hide the form
    form.setAttribute('method', 'post');
    form.setAttribute('action', '/edit_quiz/{{ quiz.id }}'); // Ensure correct Flask URL
    form.setAttribute('enctype', 'multipart/form-data'); // Ensure correct enctype

    // Add hidden input for question ID
    var inputQuestionId = document.createElement('input');
    inputQuestionId.type = 'hidden';
    inputQuestionId.name = 'newQuestionId';
    inputQuestionId.value = questionId;
    form.appendChild(inputQuestionId);

    // Add other inputs for question data
    var questionText = newQuestion.querySelector('textarea[name="newQuestionText"]').value;
    var inputQuestionText = document.createElement('input');
    inputQuestionText.type = 'hidden';
    inputQuestionText.name = 'newQuestionText';
    inputQuestionText.value = questionText;
    form.appendChild(inputQuestionText);

    var questionType = newQuestion.querySelector('select[name="newQuestionType"]').value;
    var inputQuestionType = document.createElement('input');
    inputQuestionType.type = 'hidden';
    inputQuestionType.name = 'newQuestionType';
    inputQuestionType.value = questionType;
    form.appendChild(inputQuestionType);

    // Append the form to the body and submit
    document.body.appendChild(form);
    form.submit();
}


function handleQuestionTypeChange(selectElement, questionId) {
    var questionContainer = selectElement.closest('.question-container');
    var optionsContainer = questionContainer.querySelector('.options-container');
    var trueFalseContainer = questionContainer.querySelector('.true-false-container');
    var completeContainer = questionContainer.querySelector('.complete-container');

    if (selectElement.value === 'multiple') {
        optionsContainer.style.display = 'block';
        trueFalseContainer.style.display = 'none';
        completeContainer.style.display = 'none';
    } else if (selectElement.value === 'true_false') {
        optionsContainer.style.display = 'none';
        trueFalseContainer.style.display = 'block';
        completeContainer.style.display = 'none';
    } else if (selectElement.value === 'complete') {
        optionsContainer.style.display = 'none';
        trueFalseContainer.style.display = 'none';
        completeContainer.style.display = 'block';
    }
}

function deleteQuestion(questionId) {
    var questionElement = document.getElementById(`question${questionId}`);
    if (questionElement) {
        var confirmDelete = confirm("Are you sure you want to delete this question?");
        if (confirmDelete) {
            // Send a DELETE request to the server
            fetch(`/delete_question/${questionId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                // Remove the question element from the DOM on successful deletion
                questionElement.remove();
                return response.json();
            })
            .then(data => {
                // Optionally handle success message or other actions
                console.log(data.message); // Log success message
            })
            .catch(error => {
                console.error('Error:', error);
                // Handle error scenario if needed
            });
        }
    }
}


// Initial setup if there are existing questions to show
document.addEventListener('DOMContentLoaded', function() {
    var existingQuestions = document.querySelectorAll('.question-container');
    existingQuestions.forEach(function(questionElement) {
        var questionId = questionElement.id.replace('question', '');
        var questionTypeSelect = document.getElementById(`questionType${questionId}`);
        if (questionTypeSelect) {
            handleQuestionTypeChange(questionTypeSelect, questionId);
        }
    });
});
