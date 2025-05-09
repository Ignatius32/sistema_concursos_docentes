// IMPORTANT: Make sure to add GOOGLE_DRIVE_SECURE_TOKEN in Script Properties with the value from your .env file

// The TEMPLATES mapping is no longer needed as template IDs are passed directly from the backend
// Keeping this commented for backward compatibility reference
/*
const TEMPLATES = {
  'resLlamadoTribunalInterino': '1Sb8TI4AJM6bIu-I-xGB-44ST6AltcQwIGZyN6F-sKHc', 
  'resLlamadoRegular': '1Eg0N5s4H_wGEHUZClYZs-jF4ED2pjHbT-KsUoSSLOX8',
  'resTribunalRegular': '119a255YfBWEdqu_IEJT1vYWSLAP9KhVk4G5NHPTYD6Q',
  'actaConstitucionTribunalRegular': '1Gid4o-lkDfuhNb0g_QHdVvlPoQfS5lR8AtnIxtuLsdI',
};
*/

// Utility functions
function sanitizeFolderName(name) {
  // First normalize accented characters
  const normalized = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  // Then replace any remaining invalid characters with underscore
  return normalized.replace(/[^a-z0-9]/gi, '_');
}

function verifyToken(token) {
  var scriptProperties = PropertiesService.getScriptProperties();
  var validToken = scriptProperties.getProperty('GOOGLE_DRIVE_SECURE_TOKEN');
  return token === validToken;
}

// Function to add a signature stamp to a PDF
function addSignatureToPdf(fileId, nombre, apellido, dni, firmaCount) {
  // Verify the file exists and is accessible
  var file;
  try {
    file = DriveApp.getFileById(fileId);
  } catch (e) {
    throw new Error("File not found or not accessible: " + e.message);
  }
  
  // Get the file content as PDF
  var fileBlob = file.getBlob();
  var pdfBytes = fileBlob.getBytes();
  
  // Create a temporary file to store the PDF
  var tempFile = DriveApp.createFile(fileBlob);
  
  // Use PDF.js library or Google's built-in PDF service to add a signature
  // For now, we'll use a simpler text-based approach
  
  // Get the current timestamp
  var timestamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd/MM/yyyy HH:mm:ss");
  
  // Create signature text with metadata
  var signature = "Firmado por: " + apellido + ", " + nombre + " (DNI: " + dni + ") - " + timestamp;
  
  // Calculate position based on signature count
  // Each signature will be placed at a different position
  // Base signature position
  var yPosition = 20 + (12 * firmaCount); // Start at 20 points from bottom, add 12 points for each signature
  
  // Maximum of 10 signatures before starting a second column
  var xOffset = 0;
  if (firmaCount >= 10) {
    // Use columns for overflow signatures
    var column = Math.floor(firmaCount / 10) + 1;
    yPosition = 20 + (12 * (firmaCount % 10));
    xOffset = -200 * column; // Move left for each additional column
  }
  
  // Get parent folder to upload stamped PDF
  var parentFolder = file.getParents().next();
  
  // Generate a new filename
  var newFilename = file.getName().replace(".pdf", "") + "_signed_" + firmaCount + ".pdf";
  
  // Add the signature stamp to the PDF
  // This is a simplified version - in a real implementation you would use PDF libraries
  var stampedPdfBytes = addTextStampToPdf(pdfBytes, signature, yPosition, xOffset, firmaCount);
  
  // Create a new file with the stamped PDF
  var stampedFile = parentFolder.createFile(Utilities.newBlob(stampedPdfBytes, "application/pdf", newFilename));
  
  // Clean up the temporary file
  tempFile.setTrashed(true);
  
  // Return the new file information
  return {
    fileId: stampedFile.getId(),
    webViewLink: stampedFile.getUrl()
  };
}

// Helper function to add a text stamp to a PDF (placeholder implementation)
function addTextStampToPdf(pdfBytes, signature, yPosition, xOffset, firmaCount) {
  // In a real implementation, this would use PDF libraries to properly stamp the document
  // For now, returning the original bytes as a placeholder
  
  // Note: In a production environment, you would:
  // 1. Use a PDF manipulation library to add the text at the specific position
  // 2. Consider adding a visual border or background to the signature
  // 3. Properly handle multi-page documents
  
  return pdfBytes;
}

// Function to get file content
function getFileContent(fileId) {
  // Verify the file exists and is accessible
  var file;
  try {
    file = DriveApp.getFileById(fileId);
  } catch (e) {
    throw new Error("File not found or not accessible: " + e.message);
  }
  
  // Get the file content as bytes and encode as base64
  var fileBlob = file.getBlob();
  var bytes = fileBlob.getBytes();
  var base64Content = Utilities.base64Encode(bytes);
  
  return {
    fileId: fileId,
    fileName: file.getName(),
    fileData: base64Content,
    mimeType: file.getMimeType()
  };
}

// Function to send email with attachments and placeholder support
function sendEmail(to, subject, htmlBody, senderName, attachmentIds, placeholders) {
  // Basic validation
  if (!to || !subject || !htmlBody) {
    throw new Error("Recipient, subject, and body are required.");
  }

  try {
    // Process placeholders in subject and body if provided
    if (placeholders) {
      Object.keys(placeholders).forEach(function(key) {
        const placeholder = '<<' + key + '>>';
        subject = subject.replace(new RegExp(placeholder, 'g'), placeholders[key] || '');
        htmlBody = htmlBody.replace(new RegExp(placeholder, 'g'), placeholders[key] || '');
      });
    }
    
    // Configure email options
    let options = {
      htmlBody: htmlBody,
      name: senderName || 'Sistema de Concursos Docentes'
    };
    
    // Add attachments if provided
    if (attachmentIds && attachmentIds.length > 0) {
      const attachments = attachmentIds.map(fileId => {
        // Get the original file
        const file = DriveApp.getFileById(fileId);
        const mimeType = file.getMimeType();
        
        // If it's a PDF, keep it as is
        if (mimeType === MimeType.PDF) {
          return file.getBlob();
        }
        
        // If it's a Google Doc, use the export method
        if (mimeType === MimeType.GOOGLE_DOCS) {
          try {
            const url = "https://www.googleapis.com/drive/v3/files/" + fileId + "/export?mimeType=application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            const token = ScriptApp.getOAuthToken();
            const response = UrlFetchApp.fetch(url, {
              headers: {
                'Authorization': 'Bearer ' + token
              }
            });
            const blob = response.getBlob();
            blob.setName(file.getName().replace(/\.[^/.]+$/, "") + ".docx");
            return blob;
          } catch (convErr) {
            // If conversion fails, try to get the document as PDF
            Logger.log("Failed to convert to DOCX: " + convErr + ". Falling back to PDF.");
            return file.getAs(MimeType.PDF);
          }
        }
        
        // For any other type, return as is
        return file.getBlob();
      });
      options.attachments = attachments;
    }
    
    // Send the email
    GmailApp.sendEmail(to, subject, '', options);
    
    return {
      success: true,
      to: to,
      subject: subject
    };
  } catch (err) {
    throw new Error("Error sending email: " + err.message);
  }
}

// Function to create a document from template
function createDocFromTemplate(templateName, data, targetFolderId, fileName) {
  // Basic validation
  if (!templateName || !data || !targetFolderId || !fileName) {
    throw new Error("Template name, data, target folder ID, and file name are required.");
  }
  
  // Get template ID from the mapping
  var templateId = TEMPLATES[templateName];
  if (!templateId) {
    throw new Error(`Unknown template: ${templateName}`);
  }
  
  try {
    // Get the template file
    var templateFile = DriveApp.getFileById(templateId);
    
    // Get the target folder
    var targetFolder = DriveApp.getFolderById(targetFolderId);
    
    // Create a copy of the template in the target folder
    var newDoc = templateFile.makeCopy(fileName, targetFolder);
    
    // Open the document for editing
    var doc = DocumentApp.openById(newDoc.getId());
    var body = doc.getBody();
    
    // Replace all placeholders with actual data
    Object.keys(data).forEach(function(key) {
      var placeholder = '<<' + key + '>>';
      body.replaceText(placeholder, data[key] || '');
    });
    
    // Save and close the document
    doc.saveAndClose();
    
    return {
      fileId: newDoc.getId(),
      webViewLink: newDoc.getUrl()
    };
  } catch (err) {
    throw new Error("Error creating document from template: " + err.message);
  }
}

// Function to create a contest folder under a specific root folder.
function crearConcurso(folderName) {
  // Basic validation
  if (!folderName) {
    throw new Error("Folder name is required.");
  }

  // Sanitize the folder name
  var sanitizedName = sanitizeFolderName(folderName);
  
  // Your folder ID from the Google Drive URL
  var root = DriveApp.getFolderById("1BD6fp88EQTwW9yhw4USkJjaRlbmeSHHa");
  
  // Check if a folder with the same name already exists.
  var folders = root.getFoldersByName(sanitizedName);
  if (folders.hasNext()) {
    throw new Error("Folder already exists.");
  }
  
  // Create the new folder with sanitized name
  var newFolder = root.createFolder(sanitizedName);
  
  return {
    folderId: newFolder.getId()
  };
}

// Function to create a nested folder inside a parent folder
function createNestedFolder(parentFolderId, folderName) {
  // Get parent folder
  var parentFolder = DriveApp.getFolderById(parentFolderId);
  
  // Sanitize folder name
  var sanitizedName = sanitizeFolderName(folderName);
  
  // Check if folder already exists
  var folders = parentFolder.getFoldersByName(sanitizedName);
  if (folders.hasNext()) {
    throw new Error("Folder already exists.");
  }
  
  // Create new folder
  var newFolder = parentFolder.createFolder(sanitizedName);
  return newFolder.getId();
}

// Function to create a postulante folder inside a concurso folder
function crearPostulante(concursoFolderId, folderName) {
  // Basic validation
  if (!concursoFolderId || !folderName) {
    throw new Error("Concurso folder ID and folder name are required.");
  }

  // Sanitize the folder name
  var sanitizedName = sanitizeFolderName(folderName);
  
  // Get the concurso folder
  var concursoFolder = DriveApp.getFolderById(concursoFolderId);
  
  // Check if a folder with the same name already exists
  var folders = concursoFolder.getFoldersByName(sanitizedName);
  if (folders.hasNext()) {
    throw new Error("Folder already exists.");
  }
  
  // Create the new folder with sanitized name inside the concurso folder
  var newFolder = concursoFolder.createFolder(sanitizedName);
  return newFolder.getId();
}

// Function to upload a file to a specific folder
function uploadFile(folderId, fileName, fileData, mimeType) {
  // Basic validation
  if (!folderId || !fileName || !fileData) {
    throw new Error("Folder ID, file name and file data are required.");
  }

  if (!mimeType) {
    mimeType = "application/octet-stream"; // Default MIME type if not provided
  }

  try {
    // Get the folder
    var folder = DriveApp.getFolderById(folderId);
    
    // Convert base64 data to bytes
    var decodedData = Utilities.base64Decode(fileData);
    var blob = Utilities.newBlob(decodedData, mimeType, fileName);
    
    // Create the file in Drive
    var file = folder.createFile(blob);
    
    return {
      fileId: file.getId(),
      webViewLink: file.getUrl()
    };
  } catch (err) {
    throw new Error("Error uploading file: " + err.message);
  }
}

// Function to delete a file from Drive
function deleteFile(fileId) {
  // Basic validation
  if (!fileId) {
    throw new Error("File ID is required.");
  }

  try {
    // Get the file and delete it
    var file = DriveApp.getFileById(fileId);
    file.setTrashed(true);
    return true;
  } catch (err) {
    throw new Error("Error deleting file: " + err.message);
  }
}

// Function to delete a folder from Drive
function deleteFolder(folderId) {
  // Basic validation
  if (!folderId) {
    throw new Error("Folder ID is required.");
  }

  try {
    // Get the folder and delete it
    var folder = DriveApp.getFolderById(folderId);
    folder.setTrashed(true);
    return true;
  } catch (err) {
    throw new Error("Error deleting folder: " + err.message);
  }
}

// Function to overwrite an existing file
function overwriteFile(fileId, fileData, mimeType) {
  // Basic validation
  if (!fileId || !fileData) {
    throw new Error("File ID and file data are required.");
  }

  try {
    // Get the existing file
    var existingFile = DriveApp.getFileById(fileId);
    var fileName = existingFile.getName();
    var parentFolder = existingFile.getParents().next();
    
    // Convert base64 data to bytes
    var decodedData = Utilities.base64Decode(fileData);
    
    // Create blob with explicit PDF MIME type
    var blob = Utilities.newBlob(decodedData);
    blob.setName(fileName);
    blob.setContentType(mimeType || "application/pdf");
    
    // Create new file and copy permissions
    var newFile = parentFolder.createFile(blob);
    
    // Copy permissions from old file to new file
    var permissions = existingFile.getSharingAccess();
    var isPublic = permissions == DriveApp.Access.ANYONE || permissions == DriveApp.Access.ANYONE_WITH_LINK;
    if (isPublic) {
      newFile.setSharing(permissions, DriveApp.Permission.VIEW);
    }
    
    // Delete the existing file
    existingFile.setTrashed(true);
    
    return {
      status: "success",
      fileId: newFile.getId(),
      webViewLink: newFile.getUrl(),
    };
  } catch (err) {
    throw new Error("Error overwriting file: " + err.message);
  }
}

// Function to rename a folder in Drive
function renameFolder(folderId, newName) {
  // Basic validation
  if (!folderId || !newName) {
    throw new Error("Folder ID and new name are required.");
  }

  // Sanitize the new folder name
  var sanitizedName = sanitizeFolderName(newName);

  try {
    // Get the folder and rename it
    var folder = DriveApp.getFolderById(folderId);
    folder.setName(sanitizedName);
    return true;
  } catch (err) {
    throw new Error("Error renaming folder: " + err.message);
  }
}

// Function to handle HTTP requests
function doPost(e) {
  // Verify secure token using correct property name
  const secureToken = PropertiesService.getScriptProperties().getProperty('GOOGLE_DRIVE_SECURE_TOKEN');
  
  try {
    // Parse request data
    const data = JSON.parse(e.postData.contents);
    
    // Verify token for security
    if (data.token !== secureToken) {
      return createErrorResponse('Invalid token');
    }
    
    // Route the request to the appropriate function
    switch (data.action) {
      case 'createFolder':
        return handleCreateFolder(data);
      case 'createNestedFolder':
        return handleCreateNestedFolder(data);
      case 'createPostulanteFolder':
        return handleCreatePostulanteFolder(data);
      case 'createDocFromTemplate':
        return handleCreateDocFromTemplate(data);
      case 'uploadFile':
        return handleUploadFile(data);
      case 'getFileContent':
        return handleGetFileContent(data);
      case 'addSignatureToPdf':
        return handleAddSignatureToPdf(data);
      case 'deleteFile':
        return handleDeleteFile(data);
      case 'overwriteFile':
        return handleOverwriteFile(data);
      case 'deleteFolder':
        return handleDeleteFolder(data);
      case 'renameFolder':
        return handleRenameFolder(data);
      case 'sendEmail':
        return handleSendEmail(data);
      default:
        return createErrorResponse(`Unknown action: ${data.action}`);
    }
  } catch (error) {
    return createErrorResponse(`Error processing request: ${error.toString()}`);
  }
}

// Response creators
function createSuccessResponse(data) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "success",
    ...data
  })).setMimeType(ContentService.MimeType.JSON);
}

function createErrorResponse(message) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "error",
    message: message
  })).setMimeType(ContentService.MimeType.JSON);
}

// Action handlers
function handleCreateFolder(data) {
  if (!data.folderName) {
    throw new Error("Folder name is required.");
  }

  // Sanitize the folder name
  var sanitizedName = sanitizeFolderName(data.folderName);
  
  // Your folder ID from the Google Drive URL
  var root = DriveApp.getFolderById("1BD6fp88EQTwW9yhw4USkJjaRlbmeSHHa");
  
  // Check if a folder with the same name already exists
  var folders = root.getFoldersByName(sanitizedName);
  if (folders.hasNext()) {
    throw new Error("Folder already exists.");
  }
  
  // Create the new folder with sanitized name
  var newFolder = root.createFolder(sanitizedName);
  
  return createSuccessResponse({
    folderId: newFolder.getId()
  });
}

function handleCreateNestedFolder(data) {
  if (!data.parentFolderId || !data.folderName) {
    throw new Error("Parent folder ID and folder name are required.");
  }

  var folderId = createNestedFolder(data.parentFolderId, data.folderName);
  
  return createSuccessResponse({
    folderId: folderId
  });
}

function handleCreatePostulanteFolder(data) {
  if (!data.concursoFolderId || !data.folderName) {
    throw new Error("Concurso folder ID and folder name are required.");
  }

  var folderId = createNestedFolder(data.concursoFolderId, data.folderName);
  
  return createSuccessResponse({
    folderId: folderId
  });
}

function handleCreateDocFromTemplate(data) {
  if (!data.templateId || !data.folderId || !data.fileName || !data.data) {
    throw new Error("Template ID, folder ID, file name, and data are required.");
  }
  
  // Get the template file directly using the ID
  var templateFile;
  try {
    templateFile = DriveApp.getFileById(data.templateId);
  } catch (err) {
    throw new Error("Template not found: " + err.message);
  }
  
  // Create a copy in the destination folder
  var folder = DriveApp.getFolderById(data.folderId);
  var newDoc = templateFile.makeCopy(data.fileName, folder);
  
  // Get the document body as Google Docs document
  var doc = DocumentApp.openById(newDoc.getId());
  var body = doc.getBody();
  
  // Replace all placeholders
  for (var key in data.data) {
    body.replaceText('<<' + key + '>>', data.data[key] || '');
  }
  
  // Save and close the document
  doc.saveAndClose();
  
  return createSuccessResponse({
    fileId: newDoc.getId(),
    webViewLink: newDoc.getUrl()
  });
}

function handleUploadFile(data) {
  if (!data.folderId || !data.fileName || !data.fileData) {
    throw new Error("Folder ID, file name, and file data are required.");
  }
  
  // Use the provided MIME type or default to application/pdf
  var mimeType = data.mimeType || "application/pdf";
  
  // Decode base64 file data
  var blob = Utilities.newBlob(Utilities.base64Decode(data.fileData), mimeType, data.fileName);
  
  // Get the destination folder
  var folder = DriveApp.getFolderById(data.folderId);
  
  // Create the file
  var file = folder.createFile(blob);
  
  return createSuccessResponse({
    fileId: file.getId(),
    webViewLink: file.getUrl()
  });
}

function handleDeleteFile(data) {
  if (!data.fileId) {
    throw new Error("File ID is required.");
  }
  
  var file = DriveApp.getFileById(data.fileId);
  file.setTrashed(true);
  
  return createSuccessResponse({
    success: true
  });
}

function handleDeleteFolder(data) {
  if (!data.folderId) {
    throw new Error("Folder ID is required.");
  }
  
  var folder = DriveApp.getFolderById(data.folderId);
  folder.setTrashed(true);
  
  return createSuccessResponse({
    success: true
  });
}

function handleOverwriteFile(data) {
  // Basic validation
  if (!data.fileId || !data.fileData) {
    throw new Error("File ID and file data are required.");
  }

  try {
    // Get the existing file to copy its permissions
    var existingFile = DriveApp.getFileById(data.fileId);
    var fileName = existingFile.getName();
    var parentFolder = existingFile.getParents().next();
    
    // Decode base64 file data
    var decodedData = Utilities.base64Decode(data.fileData);
    
    // Create a new blob with explicit PDF mime type
    var blob = Utilities.newBlob(decodedData, "application/pdf", fileName);
    
    // Create a new file with the updated content
    var newFile = parentFolder.createFile(blob);
    
    // Copy sharing permissions from old file
    var permissions = existingFile.getSharingAccess();
    var permissionType = existingFile.getSharingPermission();
    newFile.setSharing(permissions, permissionType);
    
    // If the file was publicly accessible, make sure to maintain that
    if (existingFile.isShareableByEditors()) {
      newFile.setShareableByEditors(true);
    }
    
    // Move the old file to trash
    existingFile.setTrashed(true);
    
    return createSuccessResponse({
      fileId: newFile.getId(),
      webViewLink: newFile.getUrl()
    });
    
  } catch (err) {
    return createErrorResponse("Error overwriting file: " + err.toString());
  }
}

function handleRenameFolder(data) {
  if (!data.folderId || !data.newName) {
    throw new Error("Folder ID and new name are required.");
  }
  
  var folder = DriveApp.getFolderById(data.folderId);
  var sanitizedName = sanitizeFolderName(data.newName);
  folder.setName(sanitizedName);
  
  return createSuccessResponse({
    success: true
  });
}

// Add handler for send email action
function handleSendEmail(data) {
  if (!data.to || !data.subject || !data.htmlBody) {
    throw new Error("Recipient, subject, and HTML body are required.");
  }
  
  const result = sendEmail(
    data.to,
    data.subject,
    data.htmlBody,
    data.senderName || null,
    data.attachmentIds || [],
    data.placeholders || null
  );
  
  return createSuccessResponse(result);
}

// Handler for getting file content
function handleGetFileContent(data) {
  if (!data.fileId) {
    throw new Error("File ID is required.");
  }
  
  try {
    const file = DriveApp.getFileById(data.fileId);
    const blob = file.getBlob();
    const content = blob.getBytes();
    const base64Content = Utilities.base64Encode(content);
    
    return createSuccessResponse({
      fileData: base64Content,
      fileName: file.getName(),
      mimeType: file.getMimeType() || 'application/pdf'
    });
  } catch (err) {
    return createErrorResponse("Error getting file content: " + err.toString());
  }
}

// Handler for adding signature to PDF
function handleAddSignatureToPdf(data) {
  if (!data.fileId || !data.nombre || !data.apellido || !data.dni) {
    throw new Error("File ID, nombre, apellido, and DNI are required.");
  }
  
  const result = addSignatureToPdf(
    data.fileId,
    data.nombre,
    data.apellido,
    data.dni,
    data.firmaCount || 0
  );
  
  return createSuccessResponse(result);
}

// Handler for overwriting file
function handleOverwriteFile(data) {
  if (!data.fileId || !data.fileData) {
    throw new Error("File ID and file data are required.");
  }
  
  try {
    // Get the existing file
    const existingFile = DriveApp.getFileById(data.fileId);
    const fileName = existingFile.getName();
    const parentFolder = existingFile.getParents().next();
    
    // Decode base64 data to bytes
    const decodedData = Utilities.base64Decode(data.fileData);
    
    // Create blob with PDF MIME type
    const blob = Utilities.newBlob(decodedData, 'application/pdf', fileName);
    
    // Create new file
    const newFile = parentFolder.createFile(blob);
    
    // Copy permissions from old file
    const permissions = existingFile.getSharingAccess();
    const isPublic = permissions == DriveApp.Access.ANYONE || 
                    permissions == DriveApp.Access.ANYONE_WITH_LINK;
    if (isPublic) {
      newFile.setSharing(permissions, DriveApp.Permission.VIEW);
    }
    
    // Move old file to trash
    existingFile.setTrashed(true);
    
    return createSuccessResponse({
      fileId: newFile.getId(),
      webViewLink: newFile.getUrl()
    });
  } catch (err) {
    return createErrorResponse("Error overwriting file: " + err.toString());
  }
}