"""
Face Verification Views Module
Handles face verification, comparison, and watchlist verification
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import logging

from ..models import Targets_watchlist, TargetPhoto

logger = logging.getLogger(__name__)

@login_required
def face_verification(request):
    """Face verification service to compare two images and show similarity"""
    if request.method == 'POST':
        try:
            # Check if we have base64 data from preview or file uploads
            image1_base64 = request.POST.get('image1_base64')
            image2_base64 = request.POST.get('image2_base64')
            threshold = float(request.POST.get('threshold', 50)) / 100  # Convert percentage to decimal
            
            # If no base64 data, process file uploads
            if not image1_base64 or not image2_base64:
                image1 = request.FILES.get('image1')
                image2 = request.FILES.get('image2')
                
                if not image1 or not image2:
                    messages.error(request, 'Please upload both images for comparison.')
                    return render(request, 'face_verification.html')
                
                # Convert images to base64 for processing and display
                import base64
                
                def image_to_base64(image_file):
                    image_file.seek(0)
                    image_data = image_file.read()
                    return base64.b64encode(image_data).decode('utf-8')
                
                # Process images
                image1_base64 = image_to_base64(image1)
                image2_base64 = image_to_base64(image2)
                image1_name = image1.name
                image2_name = image2.name
            else:
                # Use names from preview or generate generic names
                image1_name = request.POST.get('image1_name', 'Reference Image')
                image2_name = request.POST.get('image2_name', 'Query Image')
            
            # Import face AI service
            from face_ai.services.face_detection import FaceDetectionService
            from face_ai.services.milvus_service import MilvusService
            
            face_service = FaceDetectionService()
            milvus_service = MilvusService()
            
            # CRITICAL: Validate face detection before verification
            # Check Image 1 for single face
            face1_validation = face_service.detect_faces_in_image_base64(image1_base64)
            if not face1_validation['success']:
                messages.error(request, f'Image 1: {face1_validation["error"]}')
                return render(request, 'face_verification.html')
            
            if face1_validation['faces_detected'] == 0:
                messages.error(request, 'Image 1: No faces detected. Please upload an image with a clear, visible face.')
                return render(request, 'face_verification.html')
            
            if face1_validation['faces_detected'] > 1:
                messages.error(request, f'Image 1: Multiple faces detected ({face1_validation["faces_detected"]}). Please upload an image with only one person.')
                return render(request, 'face_verification.html')
            
            # Check Image 2 for single face
            face2_validation = face_service.detect_faces_in_image_base64(image2_base64)
            if not face2_validation['success']:
                messages.error(request, f'Image 2: {face2_validation["error"]}')
                return render(request, 'face_verification.html')
            
            if face2_validation['faces_detected'] == 0:
                messages.error(request, 'Image 2: No faces detected. Please upload an image with a clear, visible face.')
                return render(request, 'face_verification.html')
            
            if face2_validation['faces_detected'] > 1:
                messages.error(request, f'Image 2: Multiple faces detected ({face2_validation["faces_detected"]}). Please upload an image with only one person.')
                return render(request, 'face_verification.html')
            
            # Validate face quality and confidence
            face1_confidence = face1_validation['faces'][0]['confidence'] if face1_validation['faces'] else 0
            face2_confidence = face2_validation['faces'][0]['confidence'] if face2_validation['faces'] else 0
            
            min_confidence = 0.6  # Minimum detection confidence
            if face1_confidence < min_confidence:
                messages.warning(request, f'Image 1: Low face detection confidence ({face1_confidence:.1%}). Results may be unreliable.')
            
            if face2_confidence < min_confidence:
                messages.warning(request, f'Image 2: Low face detection confidence ({face2_confidence:.1%}). Results may be unreliable.')
            
            # Now proceed with face verification since we have valid single faces
            result = face_service.verify_faces(image1_base64, image2_base64, threshold)
            
            if result['success']:
                # Store results for template
                context = {
                    'verification_result': result,
                    'image1_name': image1_name,
                    'image2_name': image2_name,
                    'threshold': threshold * 100,
                    'similarity_score': result['similarity_score'],
                    'is_match': result['faces_match'],  # Map faces_match to is_match for template
                    'age_estimate': result.get('face1', {}).get('age', 'N/A'),
                    'gender_estimate': result.get('face1', {}).get('gender', 'N/A'),
                    'confidence': result.get('face1', {}).get('confidence', 'N/A'),
                    'image1_base64': image1_base64,
                    'image2_base64': image2_base64,
                    'face1_confidence': face1_confidence,
                    'face2_confidence': face2_confidence,
                    'face1_bbox': face1_validation['faces'][0]['bbox'] if face1_validation['faces'] else None,
                    'face2_bbox': face2_validation['faces'][0]['bbox'] if face2_validation['faces'] else None
                }
                
                # Add success message
                if result['faces_match']:
                    messages.success(request, f'✅ Faces MATCH! Similarity: {result["similarity_score"]:.2%}')
                else:
                    messages.warning(request, f'❌ Faces DO NOT MATCH. Similarity: {result["similarity_score"]:.2%}')
                
                return render(request, 'face_verification.html', context)
            else:
                messages.error(request, f'Face verification failed: {result.get("error", "Unknown error")}')
                return render(request, 'face_verification.html')
                
        except Exception as e:
            messages.error(request, f'Error during face verification: {str(e)}')
            return render(request, 'face_verification.html')
    
    return render(request, 'face_verification.html')

@login_required
def face_verification_preview(request):
    """Preview uploaded images and validate face detection requirements before verification"""
    if request.method == 'POST':
        try:
            # Get form data
            image1 = request.FILES.get('image1')
            image2 = request.FILES.get('image2')
            threshold = float(request.POST.get('threshold', 50)) / 100
            
            if not image1 or not image2:
                messages.error(request, 'Please upload both images for comparison.')
                return render(request, 'face_verification.html')
            
            # Import face AI service
            from face_ai.services.face_detection import FaceDetectionService
            
            face_service = FaceDetectionService()
            
            # Convert images to base64 for preview and validation
            import base64
            
            def image_to_base64(image_file):
                image_file.seek(0)
                image_data = image_file.read()
                return base64.b64encode(image_data).decode('utf-8')
            
            # Process images
            img1_base64 = image_to_base64(image1)
            img2_base64 = image_to_base64(image2)
            
            # Validate face detection requirements
            face1_validation = face_service.detect_faces_in_image_base64(img1_base64)
            face2_validation = face_service.detect_faces_in_image_base64(img2_base64)
            
            # Prepare validation results
            validation_results = {
                'image1': {
                    'name': image1.name,
                    'base64': img1_base64,
                    'validation': face1_validation,
                    'status': 'valid' if face1_validation['success'] and face1_validation['faces_detected'] == 1 else 'invalid'
                },
                'image2': {
                    'name': image2.name,
                    'base64': img2_base64,
                    'validation': face2_validation,
                    'status': 'valid' if face2_validation['success'] and face2_validation['faces_detected'] == 1 else 'invalid'
                },
                'threshold': threshold * 100,
                'overall_status': 'ready' if (
                    face1_validation['success'] and face1_validation['faces_detected'] == 1 and
                    face2_validation['success'] and face2_validation['faces_detected'] == 1
                ) else 'not_ready'
            }
            
            # Add appropriate messages
            if validation_results['overall_status'] == 'ready':
                messages.success(request, '✅ Both images meet verification requirements! Ready to proceed with face verification.')
            else:
                if validation_results['image1']['status'] == 'invalid':
                    if face1_validation['faces_detected'] == 0:
                        messages.error(request, f'❌ {image1.name}: No faces detected. Please upload an image with a clear, visible face.')
                    elif face1_validation['faces_detected'] > 1:
                        messages.error(request, f'❌ {image1.name}: Multiple faces detected ({face1_validation["faces_detected"]}). Please upload an image with only one person.')
                    else:
                        messages.error(request, f'❌ {image1.name}: Face detection failed. Please try a different image.')
                
                if validation_results['image2']['status'] == 'invalid':
                    if face2_validation['faces_detected'] == 0:
                        messages.error(request, f'❌ {image2.name}: No faces detected. Please upload an image with a clear, visible face.')
                    elif face2_validation['faces_detected'] > 1:
                        messages.error(request, f'❌ {image2.name}: Multiple faces detected ({face2_validation["faces_detected"]}). Please upload an image with only one person.')
                    else:
                        messages.error(request, f'❌ {image2.name}: Face detection failed. Please try a different image.')
                
                messages.warning(request, '⚠️ Please fix the issues above before proceeding with face verification.')
            
            return render(request, 'face_verification_preview.html', validation_results)
                
        except Exception as e:
            messages.error(request, f'Error during image validation: {str(e)}')
            return render(request, 'face_verification.html')
    
    return redirect('face_verification')

@login_required
def face_verification_watchlist(request):
    """Advanced watchlist verification with multiple modes"""
    # Get all watchlist targets for selection
    watchlist_targets = Targets_watchlist.objects.select_related('case').all()
    
    if request.method == 'POST':
        try:
            verification_mode = request.POST.get('verification_mode')
            threshold = float(request.POST.get('threshold', 60)) / 100
            max_results = int(request.POST.get('max_results', 5))
            
            if verification_mode == 'mode1':
                # Mode 1: Watchlist vs Image
                return handle_mode1_verification(request, watchlist_targets, threshold, max_results)
            elif verification_mode == 'mode2':
                # Mode 2: Watchlist vs Watchlist
                return handle_mode2_verification(request, watchlist_targets, threshold, max_results)
            else:
                messages.error(request, 'Invalid verification mode selected.')
                return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
                
        except Exception as e:
            messages.error(request, f'Error during watchlist verification: {str(e)}')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
    
    return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})

def handle_mode1_verification(request, watchlist_targets, threshold, max_results):
    """Handle Mode 1: Compare selected watchlist targets against one image"""
    try:
        query_image = request.FILES.get('query_image')
        target_ids = request.POST.getlist('target_ids')
        
        if not query_image:
            messages.error(request, 'Please upload an image for verification.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        if not target_ids:
            messages.error(request, 'Please select at least one watchlist target.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Import services
        from face_ai.services.face_detection import FaceDetectionService
        from face_ai.services.milvus_service import MilvusService
        
        face_service = FaceDetectionService()
        milvus_service = MilvusService()
        
        # Convert image to base64 for processing
        import base64
        
        def image_to_base64(image_file):
            image_file.seek(0)
            image_data = image_file.read()
            return base64.b64encode(image_data).decode('utf-8')
        
        # Process query image
        query_base64 = image_to_base64(query_image)
        
        # Validate face detection in query image
        query_validation = face_service.detect_faces_in_image_base64(query_base64)
        if not query_validation['success']:
            messages.error(request, f'Face detection failed: {query_validation["error"]}')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        if query_validation['faces_detected'] == 0:
            messages.error(request, 'No faces detected in the uploaded image. Please upload an image with a clear, visible face.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        if query_validation['faces_detected'] > 1:
            messages.error(request, f'Multiple faces detected ({query_validation["faces_detected"]}). Please upload an image with only one person.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Get the face embedding from query image
        query_face = query_validation['faces'][0]
        query_embedding = face_service.app.get(face_service._base64_to_image(query_base64))[0].normed_embedding
        
        # Process each selected target
        verification_results = []
        total_targets = len(target_ids)
        
        for target_id in target_ids:
            try:
                target = Targets_watchlist.objects.get(id=target_id)
                
                # Get target photos
                target_photos = TargetPhoto.objects.filter(person=target)
                
                for photo in target_photos:
                    try:
                        # Convert photo to base64 for comparison
                        photo_base64 = face_service.image_to_base64(photo.image)
                        
                        # Compare faces
                        result = face_service.verify_faces(query_base64, photo_base64, threshold)
                        
                        if result['success'] and result['faces_match']:
                            verification_results.append({
                                'target': target,
                                'photo': photo,
                                'similarity': result['similarity_score'] * 100,
                                'confidence': query_face['confidence']
                            })
                    except Exception as e:
                        logger.error(f"Error processing photo {photo.id}: {e}")
                        continue
                        
            except Targets_watchlist.DoesNotExist:
                continue
        
        # Sort by similarity (highest first)
        verification_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Limit results per target
        if max_results > 0:
            verification_results = verification_results[:max_results * total_targets]
        
        # Prepare context
        context = {
            'watchlist_targets': watchlist_targets,
            'verification_mode': 'mode1',
            'query_image_name': query_image.name,
            'query_image_base64': query_base64,
            'threshold': threshold * 100,
            'total_targets': total_targets,
            'verification_results': verification_results,
            'total_matches': len(verification_results)
        }
        
        if verification_results:
            messages.success(request, f'Found {len(verification_results)} potential matches across {total_targets} selected targets!')
        else:
            messages.info(request, f'No matches found above {threshold * 100}% similarity threshold.')
        
        return render(request, 'face_verification_watchlist.html', context)
        
    except Exception as e:
        messages.error(request, f'Error during Mode 1 verification: {str(e)}')
        return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})

def handle_mode2_verification(request, watchlist_targets, threshold, max_results):
    """Handle Mode 2: Compare watchlist targets against each other using Milvus embeddings"""
    try:
        source_target_id = request.POST.get('source_target_id')
        target_ids = request.POST.getlist('target_ids')
        
        if not source_target_id:
            messages.error(request, 'Please select a source target.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        if not target_ids:
            messages.error(request, 'Please select at least one target to compare.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Import services
        from face_ai.services.milvus_service import MilvusService
        
        milvus_service = MilvusService()
        
        # Check Milvus collection status first
        collection_status = milvus_service.check_collection_status()
        if collection_status['status'] == 'error':
            logger.error(f"Milvus collection error: {collection_status['message']}")
            messages.error(request, f'Milvus collection error: {collection_status["message"]}')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        elif collection_status['status'] == 'warning':
            logger.warning(f"Milvus collection has issues: {collection_status['message']}")
            messages.warning(request, f'Milvus collection has issues, attempting to continue with limited functionality: {collection_status["message"]}')
            # Continue with limited functionality instead of failing completely
        else:
            logger.info(f"Milvus collection status: {collection_status}")
        
        # Get source target
        try:
            source_target = Targets_watchlist.objects.get(id=source_target_id)
        except Targets_watchlist.DoesNotExist:
            messages.error(request, 'Source target not found.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Get source target photos and their Milvus embeddings
        source_photos = TargetPhoto.objects.filter(person=source_target)
        if not source_photos.exists():
            messages.error(request, 'Source target has no photos for comparison.')
            return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
        
        # Process each target to compare using normalized target embeddings
        verification_results = []
        total_targets = len(target_ids)
        
        # Debug logging
        logger.info(f"Mode 2: Processing {total_targets} targets against source target {source_target.target_name}")
        logger.info(f"Source target has {source_photos.count()} photos")
        
        # Get the source target's normalized embedding
        source_embedding = milvus_service.get_target_normalized_embedding(str(source_target.id))
        if not source_embedding:
            logger.warning(f"No normalized embedding found for source target {source_target.target_name}")
            messages.warning(request, f'No normalized embedding found for source target {source_target.target_name}. Please ensure photos are processed through the face-ai system first.')
            return render(request, 'face_verification_watchlist.html', {
                'watchlist_targets': watchlist_targets,
                'verification_mode': 'mode2',
                'source_target_name': source_target.target_name,
                'threshold': threshold * 100,
                'total_targets': total_targets,
                'verification_results': [],
                'total_matches': 0,
                'error_message': f'No normalized embedding found for source target {source_target.target_name}. Please ensure photos are processed through the face-ai system first.'
            })
        
        logger.info(f"Found normalized embedding for source target {source_target.target_name}")
        
        # Search for similar targets using the source target's normalized embedding
        search_results = milvus_service.search_similar_targets(
            source_embedding, 
            top_k=max_results * total_targets,  # Get enough results for all targets
            threshold=threshold
        )
        
        logger.info(f"Milvus search returned {len(search_results)} similar targets")
        
        # Process search results and get target information
        for result in search_results:
            try:
                result_target_id = result.get('target_id')
                similarity = result.get('similarity', 0)
                
                # Skip if this is the source target itself
                if str(result_target_id) == str(source_target.id):
                    continue
                
                # Check if this result is in our selected targets
                if str(result_target_id) in target_ids:
                    # Get the target information
                    target = Targets_watchlist.objects.get(id=result_target_id)
                    
                    # Get a representative photo for display
                    photo = TargetPhoto.objects.filter(person=target).first()
                    
                    if photo:
                        verification_results.append({
                            'target': target,
                            'photo': photo,
                            'similarity': similarity * 100,  # Convert to percentage
                            'milvus_id': result.get('id'),
                            'confidence': result.get('confidence', 0)
                        })
                        logger.info(f"Added verification result for {target.target_name} with similarity {similarity * 100:.1f}%")
                        
            except Exception as e:
                logger.error(f"Error processing search result: {e}")
                continue
                            
            except Targets_watchlist.DoesNotExist:
                continue
        
        # Sort by similarity (highest first)
        verification_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Remove duplicates (same target-photo combination)
        seen_combinations = set()
        unique_results = []
        for result in verification_results:
            combination = (result['target'].id, result['photo'].id)
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                unique_results.append(result)
        
        verification_results = unique_results
        
        # Limit results per target
        if max_results > 0:
            verification_results = verification_results[:max_results * total_targets]
        
        # Prepare context
        context = {
            'watchlist_targets': watchlist_targets,
            'verification_mode': 'mode2',
            'source_target_name': source_target.target_name,
            'threshold': threshold * 100,
            'total_targets': total_targets,
            'verification_results': verification_results,
            'total_matches': len(verification_results)
        }
        
        if verification_results:
            messages.success(request, f'Found {len(verification_results)} potential matches across {total_targets} targets using Milvus embeddings!')
        else:
            messages.info(request, f'No matches found above {threshold * 100}% similarity threshold.')
            # Add debug info to help troubleshoot
            messages.warning(request, 'Debug: Check logs for detailed information about the verification process.')
        
        return render(request, 'face_verification_watchlist.html', context)
        
    except Exception as e:
        messages.error(request, f'Error during Mode 2 verification: {str(e)}')
        return render(request, 'face_verification_watchlist.html', {'watchlist_targets': watchlist_targets})
